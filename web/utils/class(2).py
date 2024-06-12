class AC():
    def __init__(self, args):
        self.config = args
        torch.backends.cudnn.benchmark = True
        self._build()

    def train(self):
        vqvae = self.model.eval()
        gpt = self.model2.train()
        gpt.module.freeze_drop()

        config = self.config
        ddm = []
        if hasattr(config, 'demo') and config.demo:
            ddm = True
        else:
            ddm = False
        data = self.config.data
        # criterion = nn.MSELoss()
        training_data = self.training_data
        test_loader = self.test_loader
        optimizer = self.optimizer
        log = Logger(self.config, self.expdir)
        updates = 0

        checkpoint = torch.load(config.vqvae_weight)
        vqvae.load_state_dict(checkpoint['model'], strict=False)

        if hasattr(config, 'init_weight') and config.init_weight is not None and config.init_weight is not '':
            print('Use pretrained model!')
            print(config.init_weight)
            checkpoint = torch.load(config.init_weight)
            gpt.load_state_dict(checkpoint['model'], strict=False)
        # self.model.eval()

        random.seed(config.seed)
        torch.manual_seed(config.seed)
        # if args.cuda:
        torch.cuda.manual_seed(config.seed)
        self.device = torch.device('cuda' if config.cuda else 'cpu')

        # Training Loop
        for epoch_i in range(1, config.epoch + 1):

            # At the very begining, generate the motion as test
            dance_up_seqs = []
            dance_down_seqs = []
            music_seqs = []
            beat_seqs = []
            for batch_i, batch in enumerate(test_loader):
                if hasattr(config, 'demo') and config.demo:
                    # print('demo!!')
                    # ddm = True
                    music_seq = batch.to(self.device)
                    x = (
                    torch.ones(1, 1, ).to(self.device).long() * 423, torch.ones(1, 1, ).to(self.device).long() * 12)
                else:
                    music_seq, pose_seq = batch
                    music_seq = music_seq.to(self.device)
                    pose_seq = pose_seq.to(self.device)

                    pose_seq[:, :, :3] = 0
                    # print(pose_seq.size())

                music_ds_rate = config.ds_rate if not hasattr(config, 'external_wav') else config.external_wav_rate
                music_seq = music_seq[:, :, :config.structure_generate.n_music // music_ds_rate].contiguous().float()
                # print(music_seq.size())
                b, t, c = music_seq.size()
                music_seq_ori = music_seq.view(b, t // music_ds_rate, c * music_ds_rate)

                # 1. generate motion on whole music (no grad)
                ##NOTE the generation here should be consistent with the evaluation process (generate whole piece)
                with torch.no_grad():
                    if hasattr(config, 'demo') and config.demo:
                        x = x
                    else:
                        quants_pred = vqvae.module.encode(pose_seq)
                        if isinstance(quants_pred, tuple):
                            quants = tuple(
                                quants_pred[ii][0][:, :-1].clone().detach() for ii in range(len(quants_pred)))
                            x = tuple(quants_pred[i][0][:, :1] for i in range(len(quants_pred)))
                        else:
                            quants = quants_pred[0]
                            x = quants_pred[0][:, :1]

                    gpt.eval()
                    # music [1 ... 29], pose [0]
                    music_seq = music_seq_ori[:, 1:]
                    # print(z.size())
                    zs = gpt.module.sample(x, cond=music_seq)
                    # zs [0, ..., 29]

                    # print(self.dance_names[batch_i])
                    # print('up: ', zs[0][0][0].data.cpu().numpy())
                    # print('down: ', zs[1][0][0].data.cpu().numpy())

                    dance_up_seqs.append(zs[0][0][0].data.cpu().numpy())
                    dance_down_seqs.append(zs[1][0][0].data.cpu().numpy())
                    music_seqs.append(music_seq_ori[0].data.cpu().numpy())
                    beat_seqs.append(get_beat(self.dance_names[batch_i], config.rl_music_root))

            # 2. sample music-motion pair from generated data
            training_data = prepare_dataloader(music_seqs, (dance_up_seqs, dance_down_seqs), beat_seqs,
                                               self.config.batch_size, self.config.structure_generate.block_size + 1)

            log.set_progress(epoch_i, len(training_data))

            # 3. for each batch
            for batch_i, batch in enumerate(training_data):
                music_seq, pose_seq_up, pose_seq_down, beat_seq, mask_seq = batch
                music_seq = music_seq.to(self.device)[:, 1:]  # music (1..29)
                pose_seq_up = pose_seq_up.to(self.device)
                pose_seq_down = pose_seq_down.to(self.device)
                beat_seq = beat_seq.to(self.device)
                mask_seq = mask_seq.to(self.device)

                quants_pred = (pose_seq_up, pose_seq_down)

                # pose_seq[:, :, :3] = 0
                if isinstance(quants_pred, tuple):
                    print("train isinstance 1")
                    # quants_input 0..28 len 29
                    quants_input = tuple(quants_pred[ii][:, :-1].clone().detach() for ii in range(len(quants_pred)))
                    # quants_output 1..29 len 29
                    quants_target = tuple(quants_pred[ii][:, 1:].clone().detach() for ii in range(len(quants_pred)))
                    # rewards_input 1..28 len 28
                    rewards_input = tuple([quants_pred[ii][:, 1:-1].clone().detach()] for ii in range(len(quants_pred)))
                    # actor input 0..27 len 28
                    quants_actor_input = tuple(
                        quants_pred[ii][:, :-2].clone().detach() for ii in range(len(quants_pred)))
                    # actor output 1..28 len 28
                    quants_actor_output = tuple(
                        quants_pred[ii][:, 1:-1].clone().detach() for ii in range(len(quants_pred)))

                else:
                    print("train isinstance 2")
                    quants = quants_pred[0]
                    quants_input = quants[:, :-1].clone().detach()
                    quants_target = quants[:, 1:].clone().detach()
                    rewards_input = quants[:, 1:-1].clone().detach()
                    quants_actor_input = quants[:, :-2].clone().detach()
                    quants_actor_output = quants[:, 1:-1].clone().detach()

                pose_sample = vqvae.module.decode(rewards_input)
                # pose_sample [1...28] len 28

                # 3a. compute rewards from motion (1..28, len 28) and music (1*8..28*8, len 28*8)
                rewards = self.dance_reward(pose_sample, beat_seq[:, 8:-8], config.ds_rate)
                # reward of action 0 ... 27 (dance 1...28, with music 1...28), len 28

                gpt.train()
                gpt.module.freeze_drop()
                optimizer.zero_grad()

                # 3b. If training actor net, then compute TDerror, without grad and cross_entropy_loss
                # 3c. if training critic net, then only compute TDerror, with grad

                values = gpt.module.critic(quants_input, music_seq)[:, :, 0]  # value of state [0 ... 28]
                td_error = (rewards + config.gamma * values[:, 1:]).clone().detach() - values[:,
                                                                                       :-1]  # values[1..28] - values[0..27], len 28

                with torch.no_grad():
                    gpt.eval()
                    output, actor_loss, entropy = gpt.module.actor(quants_actor_input, music_seq[:, :-1],
                                                                   quants_actor_output,
                                                                   reduction=False)  # output dance 1...28
                    gpt.train()
                    gpt.module.freeze_drop()

                # if need entropy loss;
                # entropy loss is a common regularization in RL but we don't use finally
                # 强化学习
                if hasattr(config, 'entropy_alpha'):
                    alpha = config.entropy_alpha
                    td_error = td_error.view(-1) + alpha * entropy.clone().detach()
                else:
                    alpha = 0
                    entropy = torch.zeros(td_error.view(-1).size()).cuda()

                # if training actor net:
                if epoch_i >= config.pretrain_critic_epoch and (
                        batch_i % (config.critic_iter + config.actor_iter) < config.actor_iter):
                    output, actor_loss, entropy = gpt.module.actor(quants_actor_input, music_seq[:, :-1],
                                                                   quants_actor_output,
                                                                   reduction=False)  # output dance 1...28
                    # loss = torch.sum(actor_loss * mask_seq.view(-1).clone().detach()) / torch.sum(mask_seq).clone().detach()
                    loss = torch.sum(
                        (actor_loss * td_error.view(-1).clone().detach() - alpha * entropy) * mask_seq.view(
                            -1).clone().detach()) / torch.sum(mask_seq).clone().detach() * config.actor_loss_decay

                    # loss = torch.mean(actor_loss * td_error.view(-1).clone().detach() - alpha * entropy) * config.actor_loss_decay
                    actor_loss = torch.sum(actor_loss * mask_seq.view(-1).clone().detach()) / torch.sum(
                        mask_seq).clone().detach()
                # if training critic net:
                else:
                    loss = torch.mean(td_error ** 2)

                actor_loss = actor_loss.clone().detach().mean()
                loss.backward()

                # update parameters
                optimizer.step()

                stats = {
                    'updates': updates,
                    'reward': ((rewards.view(-1) * mask_seq.view(-1)).sum() / mask_seq.sum()).detach().clone().item(),
                    'TD-error': (td_error ** 2).mean(),
                    'actor_loss': actor_loss.item(),
                    'entropy': entropy.clone().detach().mean()
                }
                # if epoch_i % self.config.log_per_updates == 0:
                log.update(stats)
                updates += 1

            checkpoint = {
                'model': gpt.state_dict(),
                'config': config,
                'epoch': epoch_i
            }

            # # Save checkpoint
            if epoch_i % config.save_per_epochs == 0 or epoch_i == 1:
                filename = os.path.join(self.ckptdir, f'epoch_{epoch_i}.pt')
                torch.save(checkpoint, filename)
            # Eval
            if epoch_i % config.test_freq == 0:  # 执行了
                with torch.no_grad():
                    print("Evaluation...")
                    gpt.eval()
                    results = []
                    random_id = 0  # np.random.randint(0, 1e4)
                    quants_out = {}
                    for i_eval, batch_eval in enumerate(tqdm(test_loader, desc='Generating Dance Poses')):

                        # Prepare data
                        if hasattr(config, 'demo') and config.demo:
                            music_seq = batch_eval.to(self.device)
                            x = (torch.ones(1, 1, ).to(self.device).long() * 423,
                                 torch.ones(1, 1, ).to(self.device).long() * 12)
                        else:
                            music_seq, pose_seq = batch_eval
                            music_seq = music_seq.to(self.device)
                            pose_seq = pose_seq.to(self.device)

                            quants = vqvae.module.encode(pose_seq)
                            # print(pose_seq.size())
                            if isinstance(quants, tuple):
                                x = tuple(quants[i][0][:, :1] for i in range(len(quants)))
                            else:
                                x = quants[0][:, :1]
                        # print(x.size())
                        # print(music_seq.size())
                        music_ds_rate = config.ds_rate if not hasattr(config,
                                                                      'external_wav') else config.external_wav_rate
                        music_seq = music_seq[:, :,
                                    :config.structure_generate.n_music // music_ds_rate].contiguous().float()
                        # print(music_seq.size())
                        b, t, c = music_seq.size()
                        music_seq = music_seq.view(b, t // music_ds_rate, c * music_ds_rate)
                        music_seq = music_seq[:, 1:]
                        # print(music_seq.size())

                        # block_size = gpt.module.get_block_size()

                        zs = gpt.module.sample(x, cond=music_seq)
                        # jj = 0
                        # for k in range(music_seq.size(1)):
                        #     x_cond = x if x.size(1) <= block_size else x[:, -block_size:] # crop context if needed
                        #     music_seq_input = music_seq[:, :k+1] if k < block_size else music_seq[:, k-block_size+1:k+1]
                        #     # print(x_cond.size())
                        #     # print(music_seq_input.size())
                        #     logits, _ = gpt(x_cond, music_seq_input)
                        #     # jj += 1
                        #     # pluck the logits at the final step and scale by temperature
                        #     logits = logits[:, -1, :]
                        #     # optionally crop probabilities to only the top k options
                        #     # if top_k is not None:
                        #     #     logits = top_k_logits(logits, top_k)
                        #     # apply softmax to convert to probabilities
                        #     probs = F.softmax(logits, dim=-1)
                        #     # sample from the distribution or take the most likely
                        #     # if sample:
                        #     #     ix = torch.multinomial(probs, num_samples=1)
                        #     # else:
                        #     _, ix = torch.topk(probs, k=1, dim=-1)
                        #     # append to the sequence and continue
                        #     x = torch.cat((x, ix), dim=1)

                        # zs = [x]
                        pose_sample = vqvae.module.decode(zs)

                        if config.global_vel:
                            # print('Using predicted global velocity!')
                            global_vel = pose_sample[:, :, :3].clone()
                            pose_sample[:, 0, :3] = 0
                            for iii in range(1, pose_sample.size(1)):
                                pose_sample[:, iii, :3] = pose_sample[:, iii - 1, :3] + global_vel[:, iii - 1, :]

                        if isinstance(zs, tuple):
                            quants_out[self.dance_names[i_eval]] = tuple(
                                zs[ii][0].cpu().data.numpy()[0] for ii in range(len(zs)))
                        else:
                            quants_out[self.dance_names[i_eval]] = zs[0].cpu().data.numpy()[0]

                        results.append(pose_sample)
                    print('pose_sample shape is : ', pose_sample.shape)  # 指定保存目录
                    save_dir = '/home/gisp3/Additional_Disk_4T_1/fcy/e2d/Bailando/experiments/npy_keshihua'
                    print('pose_sample save dir is : ' + save_dir)
                    name = 'pose_sample_340.npy'
                    pose_sample_copy = pose_sample
                    np.save(os.path.join(save_dir, name), pose_sample_copy.cpu().detach().numpy())

                    visualizeAndWrite(results, config, self.visdir, self.dance_names, epoch_i, quants_out)
                gpt.train()
                gpt.module.freeze_drop()
            self.schedular.step()

    def eval(self):
        with torch.no_grad():
            vqvae = self.model.eval()
            gpt = self.model2.eval()

            config = self.config

            epoch_tested = config.testing.ckpt_epoch

            checkpoint = torch.load(config.vqvae_weight)
            vqvae.load_state_dict(checkpoint['model'], strict=False)

            ckpt_path = os.path.join(self.ckptdir, f"epoch_{epoch_tested}.pt")
            self.device = torch.device('cuda' if config.cuda else 'cpu')
            print("Evaluation...")
            checkpoint = torch.load(ckpt_path)
            gpt.load_state_dict(checkpoint['model'], strict=False)
            gpt.eval()

            results = []
            random_id = 0  # np.random.randint(0, 1e4)
            # quants = {}
            quants_out = {}
            for i_eval, batch_eval in enumerate(tqdm(self.test_loader, desc='Generating Dance Poses')):
                # 使用 tqdm 库中的 tqdm 函数来迭代 self.test_loader，并在循环中显示一个进度条，描述为"Generating Dance Poses"
                # Prepare data
                # pose_seq_eval = map(lambda x: x.to(self.device), batch_eval)
                if hasattr(config, 'demo') and config.demo:
                    music_seq = batch_eval.to(self.device)
                    quants = (
                    [torch.ones(1, 1, ).to(self.device).long() * 423], [torch.ones(1, 1, ).to(self.device).long() * 12])
                else:
                    music_seq, pose_seq = batch_eval
                    music_seq = music_seq.to(self.device)
                    pose_seq = pose_seq.to(self.device)

                    quants = vqvae.module.encode(pose_seq)
                # print(pose_seq.size())
                if isinstance(quants, tuple):
                    x = tuple(quants[i][0][:, :1] for i in range(len(quants)))
                else:
                    x = quants[0][:, :1]
                # print(x.size())
                # print(music_seq.size())
                music_ds_rate = config.ds_rate if not hasattr(config, 'external_wav') else config.external_wav_rate
                music_seq = music_seq[:, :, :config.structure_generate.n_music // music_ds_rate].contiguous().float()
                b, t, c = music_seq.size()
                music_seq = music_seq.view(b, t // music_ds_rate, c * music_ds_rate)
                music_seq = music_seq[:, 1:]
                # print(music_seq.size())

                # block_size = gpt.module.get_block_size()

                # 调用 GPT-2 模型生成姿势样本 `pose_sample`，通过给定的条件音乐序列 `music_seq`
                zs = gpt.module.sample(x, cond=music_seq)
                # jj = 0
                # for k in range(music_seq.size(1)):
                #     x_cond = x if x.size(1) <= block_size else x[:, -block_size:] # crop context if needed
                #     music_seq_input = music_seq[:, :k+1] if k < block_size else music_seq[:, k-block_size+1:k+1]
                #     # print(x_cond.size())
                #     # print(music_seq_input.size())
                #     logits, _ = gpt(x_cond, music_seq_input)
                #     # jj += 1
                #     # pluck the logits at the final step and scale by temperature
                #     logits = logits[:, -1, :]
                #     # optionally crop probabilities to only the top k options
                #     # if top_k is not None:
                #     #     logits = top_k_logits(logits, top_k)
                #     # apply softmax to convert to probabilities
                #     probs = F.softmax(logits, dim=-1)
                #     # sample from the distribution or take the most likely
                #     # if sample:
                #     #     ix = torch.multinomial(probs, num_samples=1)
                #     # else:
                #     _, ix = torch.topk(probs, k=1, dim=-1)
                #     # append to the sequence and continue
                #     x = torch.cat((x, ix), dim=1)

                # zs = [x]
                pose_sample = vqvae.module.decode(zs)
                # print("pose_sample的shape: ", pose_sample.shape) # torch.Size([1, 3248, 72])
                if config.global_vel:
                    # print('!!!!!')
                    global_vel = pose_sample[:, :, :3].clone()
                    pose_sample[:, 0, :3] = 0
                    for iii in range(1, pose_sample.size(1)):
                        pose_sample[:, iii, :3] = pose_sample[:, iii - 1, :3] + global_vel[:, iii - 1, :]

                results.append(pose_sample)  # 给results接上pose_sample，其实就是给results赋值
                # print("pose_sample的shape: ", pose_sample.shape) # torch.Size([1, 3248, 72])
                if isinstance(zs, tuple):
                    quants_out[self.dance_names[i_eval]] = tuple(
                        zs[ii][0].cpu().data.numpy()[0] for ii in range(len(zs)))
                else:
                    quants_out[self.dance_names[i_eval]] = zs[0].cpu().data.numpy()[0]
            print("actor_sritic.py    line:436")
            # print("pose_sample的shape: ", pose_sample.shape)
            visualizeAndWrite(results, config, self.evaldir, self.dance_names, epoch_tested, quants_out)

    def visgt(self, ):
        config = self.config
        print("Visualizing ground truth")

        results = []
        random_id = 0  # np.random.randint(0, 1e4)

        for i_eval, batch_eval in enumerate(tqdm(self.test_loader, desc='Generating Dance Poses')):
            # Prepare data
            # pose_seq_eval = map(lambda x: x.to(self.device), batch_eval)
            pose_seq_eval = batch_eval

            results.append(pose_seq_eval)
        visualizeAndWrite(results, config, self.gtdir, self.dance_names, 0)

    def analyze_code(self, ):
        config = self.config
        print("Analyzing codebook")

        epoch_tested = config.testing.ckpt_epoch
        ckpt_path = os.path.join(self.ckptdir, f"epoch_{epoch_tested}.pt")
        checkpoint = torch.load(ckpt_path)
        self.model.load_state_dict(checkpoint['model'])
        model = self.model.eval()

        training_data = self.training_data
        all_quants = None

        torch.cuda.manual_seed(config.seed)
        self.device = torch.device('cuda' if config.cuda else 'cpu')
        random_id = 0  # np.random.randint(0, 1e4)

        for i_eval, batch_eval in enumerate(tqdm(self.training_data, desc='Generating Dance Poses')):
            # Prepare data
            # pose_seq_eval = map(lambda x: x.to(self.device), batch_eval)
            pose_seq_eval = batch_eval.to(self.device)

            quants = model.module.encode(pose_seq_eval)[0].cpu().data.numpy()
            all_quants = np.append(all_quants, quants.reshape(-1)) if all_quants is not None else quants.reshape(-1)

        print(all_quants)
        # exit()
        # visualizeAndWrite(results, config,self.gtdir, self.dance_names, 0)
        plt.hist(all_quants, bins=config.structure.l_bins, range=[0, config.structure.l_bins])

        log = datetime.datetime.now().strftime('%Y-%m-%d')
        plt.savefig(self.histdir1 + '/hist_epoch_' + str(epoch_tested) + '_%s.jpg' % log)  # 图片的存储
        plt.close()

    def sample(self, ):
        config = self.config
        print("Analyzing codebook")

        epoch_tested = config.testing.ckpt_epoch
        ckpt_path = os.path.join(self.ckptdir, f"epoch_{epoch_tested}.pt")
        checkpoint = torch.load(ckpt_path)
        self.model.load_state_dict(checkpoint['model'])
        model = self.model.eval()

        quants = {}

        results = []

        if hasattr(config, 'analysis_array') and config.analysis_array is not None:
            # print(config.analysis_array)
            names = [str(ii) for ii in config.analysis_array]
            print(names)
            for ii in config.analysis_array:
                print(ii)
                zs = [(ii * torch.ones((1, self.config.sample_code_length), device='cuda')).long()]
                print(zs[0].size())
                pose_sample = model.module.decode(zs)
                if config.global_vel:
                    global_vel = pose_sample[:, :, :3]
                    pose_sample[:, 0, :3] = 0
                    for iii in range(1, pose_sample.size(1)):
                        pose_sample[:, iii, :3] = pose_sample[:, iii - 1, :3] + global_vel[:, iii - 1, :]

                quants[str(ii)] = zs[0].cpu().data.numpy()[0]

                results.append(pose_sample)
        else:
            names = ['rand_seq_' + str(ii) for ii in range(10)]
            for ii in range(10):
                zs = [torch.randint(0, self.config.structure.l_bins, size=(1, self.config.sample_code_length),
                                    device='cuda')]
                pose_sample = model.module.decode(zs)
                quants['rand_seq_' + str(ii)] = zs[0].cpu().data.numpy()[0]
                if config.global_vel:
                    global_vel = pose_sample[:, :, :3]
                    pose_sample[:, 0, :3] = 0
                    for iii in range(1, pose_sample.size(1)):
                        pose_sample[:, iii, :3] = pose_sample[:, iii - 1, :3] + global_vel[:, iii - 1, :]
                results.append(pose_sample)
        visualizeAndWrite(results, config, self.sampledir, names, epoch_tested, quants)

    def _build(self):
        config = self.config
        self.start_epoch = 0
        self._dir_setting()
        self._build_model()
        if not (hasattr(config, 'need_not_train_data') and config.need_not_train_data):
            self._build_train_loader()
        if not (hasattr(config, 'need_not_test_data') and config.need_not_train_data):
            self._build_test_loader()
        self._build_optimizer()

    def _build_model(self):
        """ Define Model """
        config = self.config
        if hasattr(config.structure, 'name') and hasattr(config.structure_generate, 'name'):
            print(f'using {config.structure.name} and {config.structure_generate.name} ')
            model_class = getattr(models, config.structure.name)
            model = model_class(config.structure)

            model_class2 = getattr(models, config.structure_generate.name)
            model2 = model_class2(config.structure_generate)

            model_reward = getattr(models, config.reward.name)
            reward = model_reward(config.reward)
        else:
            raise NotImplementedError("Wrong Model Selection")

        model = nn.DataParallel(model)
        model2 = nn.DataParallel(model2)
        dance_reward = nn.DataParallel(reward)
        self.dance_reward = dance_reward.cuda()
        self.model2 = model2.cuda()
        self.model = model.cuda()

    def _build_train_loader(self):
        self.training_data = None
        # data = self.config.data
        # if data.name == "aist":
        #     print ("train with AIST++ dataset!")
        #     train_music_data, train_dance_data, _ = load_data_aist(
        #         data.train_dir, interval=data.seq_len, move=self.config.move if hasattr(self.config, 'move') else 64, rotmat=self.config.rotmat, external_wav=self.config.external_wav if hasattr(self.config, 'external_wav') else None, external_wav_rate=self.config.ds_rate//self.config.external_wav_rate if hasattr(self.config, 'external_wav_rate') else 1, music_normalize=self.config.music_normalize if hasattr(self.config, 'music_normalize') else False)
        # else:
        #     train_music_data, train_dance_data = load_data(
        #         args_train.train_dir,
        #         interval=data.seq_len,
        #         data_type=data.data_type)
        # self.training_data = prepare_dataloader(train_music_data, train_dance_data, self.config.batch_size)

    def _build_test_loader(self):
        config = self.config
        data = self.config.data
        if data.name == "aist":
            print("test with AIST++ dataset!")
            music_data, dance_data, dance_names = load_test_data_aist(
                data.test_dir, move=config.move, rotmat=config.rotmat,
                external_wav=config.external_wav if hasattr(self.config, 'external_wav') else None,
                external_wav_rate=self.config.external_wav_rate if hasattr(self.config, 'external_wav_rate') else 1,
                music_normalize=self.config.music_normalize if hasattr(self.config, 'music_normalize') else False)

        else:
            music_data, dance_data, dance_names = load_test_data(
                data.test_dir, interval=None)

        # pdb.set_trace()

        self.test_loader = torch.utils.data.DataLoader(
            MoDaSeq(music_data, dance_data),
            batch_size=1,
            shuffle=False
            # collate_fn=paired_collate_fn,
        )
        self.dance_names = dance_names
        # pdb.set_trace()
        # self.training_data = self.test_loader

    def _build_optimizer(self):
        # model = nn.DataParallel(model).to(device)
        config = self.config.optimizer
        try:
            optim = getattr(torch.optim, config.type)
        except Exception:
            raise NotImplementedError('not implemented optim method ' + config.type)

        self.optimizer = optim(itertools.chain(self.model2.module.parameters(),
                                               ),
                               **config.kwargs)
        self.schedular = torch.optim.lr_scheduler.MultiStepLR(self.optimizer, **config.schedular_kwargs)

    def _dir_setting(self):
        data = self.config.data
        self.expname = self.config.expname
        self.experiment_dir = os.path.join("./", "experiments")
        self.expdir = os.path.join(self.experiment_dir, self.expname)

        if not os.path.exists(self.expdir):
            os.mkdir(self.expdir)

        self.visdir = os.path.join(self.expdir, "vis")  # -- imgs, videos, jsons
        if not os.path.exists(self.visdir):
            os.mkdir(self.visdir)

        self.jsondir = os.path.join(self.visdir, "jsons")  # -- imgs, videos, jsons
        if not os.path.exists(self.jsondir):
            os.mkdir(self.jsondir)

        self.histdir = os.path.join(self.visdir, "hist")  # -- imgs, videos, jsons
        if not os.path.exists(self.histdir):
            os.mkdir(self.histdir)

        self.imgsdir = os.path.join(self.visdir, "imgs")  # -- imgs, videos, jsons
        if not os.path.exists(self.imgsdir):
            os.mkdir(self.imgsdir)

        self.videodir = os.path.join(self.visdir, "videos")  # -- imgs, videos, jsons
        if not os.path.exists(self.videodir):
            os.mkdir(self.videodir)

        self.ckptdir = os.path.join(self.expdir, "ckpt")
        if not os.path.exists(self.ckptdir):
            os.mkdir(self.ckptdir)

        self.evaldir = os.path.join(self.expdir, "eval")
        if not os.path.exists(self.evaldir):
            os.mkdir(self.evaldir)

        self.gtdir = os.path.join(self.expdir, "gt")
        if not os.path.exists(self.gtdir):
            os.mkdir(self.gtdir)

        self.jsondir1 = os.path.join(self.evaldir, "jsons")  # -- imgs, videos, jsons
        if not os.path.exists(self.jsondir1):
            os.mkdir(self.jsondir1)

        self.histdir1 = os.path.join(self.evaldir, "hist")  # -- imgs, videos, jsons
        if not os.path.exists(self.histdir1):
            os.mkdir(self.histdir1)

        self.imgsdir1 = os.path.join(self.evaldir, "imgs")  # -- imgs, videos, jsons
        if not os.path.exists(self.imgsdir1):
            os.mkdir(self.imgsdir1)

        self.videodir1 = os.path.join(self.evaldir, "videos")  # -- imgs, videos, jsons
        if not os.path.exists(self.videodir1):
            os.mkdir(self.videodir1)

        self.sampledir = os.path.join(self.evaldir, "samples")  # -- imgs, videos, jsons
        if not os.path.exists(self.sampledir):
            os.mkdir(self.sampledir)

        # self.ckptdir = os.path.join(self.expdir, "ckpt")
        # if not os.path.exists(self.ckptdir):
        #     os.mkdir(self.ckptdir)

class cached_property:
    def __init__(self, func):
        self.func = func
        self.attrname = None
        self.__doc__ = func.__doc__
        self.lock = RLock()

    def __set_name__(self, owner, name):
        if self.attrname is None:
            self.attrname = name
        elif name != self.attrname:
            raise TypeError(
                "Cannot assign the same cached_property to two different names "
                f"({self.attrname!r} and {name!r})."
            )

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError(
                "Cannot use cached_property instance without calling __set_name__ on it.")
        try:
            cache = instance.__dict__
        except AttributeError:  # not all objects have __dict__ (e.g. class defines slots)
            msg = (
                f"No '__dict__' attribute on {type(instance).__name__!r} "
                f"instance to cache {self.attrname!r} property."
            )
            raise TypeError(msg) from None
        val = cache.get(self.attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            with self.lock:
                # check if another thread filled cache while we awaited lock
                val = cache.get(self.attrname, _NOT_FOUND)
                if val is _NOT_FOUND:
                    val = self.func(instance)
                    try:
                        cache[self.attrname] = val
                    except TypeError:
                        msg = (
                            f"The '__dict__' attribute on {type(instance).__name__!r} instance "
                            f"does not support item assignment for caching {self.attrname!r} property."
                        )
                        raise TypeError(msg) from None
        return val


class SMPLModel(Module):
    def __init__(self, device=None, model_path='/home/fcy/e2d/Bailando/smpl/SMPL_MALE_1.0.pkl'):

        super(SMPLModel, self).__init__()
        with open(model_path, 'rb') as f:
            params = pickle.load(f, encoding='latin1')
        self.J_regressor = torch.from_numpy(
            np.array(params['J_regressor'].todense())
        ).type(torch.float64)
        self.weights = torch.from_numpy(params['weights']).type(torch.float64)
        self.posedirs = torch.from_numpy(params['posedirs']).type(torch.float64)
        self.v_template = torch.from_numpy(params['v_template']).type(torch.float64)
        self.shapedirs = torch.from_numpy(params['shapedirs']).type(torch.float64)
        self.kintree_table = params['kintree_table']
        self.faces = params['f']
        self.device = device if device is not None else torch.device('cpu')
        for name in ['J_regressor', 'weights', 'posedirs', 'v_template', 'shapedirs']:
            _tensor = getattr(self, name)
            setattr(self, name, _tensor.to(device))

    @staticmethod
    def rodrigues(r):
        """
        Rodrigues' rotation formula that turns axis-angle tensor into rotation
        matrix in a batch-ed manner.

        Parameter:
        ----------
        r: Axis-angle rotation tensor of shape [batch_size, 1, 3].

        Return:
        -------
        Rotation matrix of shape [batch_size, 3, 3].

        """
        # r = r.to(self.device)
        eps = r.clone().normal_(std=1e-8)
        theta = torch.norm(r + eps, dim=(1, 2), keepdim=True)  # dim cannot be tuple
        theta_dim = theta.shape[0]
        r_hat = r / theta
        cos = torch.cos(theta)
        z_stick = torch.zeros(theta_dim, dtype=torch.float64).to(r.device)
        m = torch.stack(
            (z_stick, -r_hat[:, 0, 2], r_hat[:, 0, 1], r_hat[:, 0, 2], z_stick,
             -r_hat[:, 0, 0], -r_hat[:, 0, 1], r_hat[:, 0, 0], z_stick), dim=1)
        m = torch.reshape(m, (-1, 3, 3))
        i_cube = (torch.eye(3, dtype=torch.float64).unsqueeze(dim=0) \
                  + torch.zeros((theta_dim, 3, 3), dtype=torch.float64)).to(r.device)
        A = r_hat.permute(0, 2, 1)
        dot = torch.matmul(A, r_hat)
        R = cos * i_cube + (1 - cos) * dot + torch.sin(theta) * m
        return R

    @staticmethod
    def with_zeros(x):
        """
        Append a [0, 0, 0, 1] tensor to a [3, 4] tensor.

        Parameter:
        ---------
        x: Tensor to be appended.

        Return:
        ------
        Tensor after appending of shape [4,4]

        """
        ones = torch.tensor([[0.0, 0.0, 0.0, 1.0]], dtype=torch.float64).to(x.device)
        ret = torch.cat((x, ones), dim=0)
        return ret

    @staticmethod
    def pack(x):
        """
        Append zero tensors of shape [4, 3] to a batch of [4, 1] shape tensor.

        Parameter:
        ----------
        x: A tensor of shape [batch_size, 4, 1]

        Return:
        ------
        A tensor of shape [batch_size, 4, 4] after appending.

        """
        zeros43 = torch.zeros((x.shape[0], 4, 3), dtype=torch.float64).to(x.device)
        ret = torch.cat((zeros43, x), dim=2)
        return ret

    def write_obj(self, verts, file_name):
        with open(file_name, 'w') as fp:
            for v in verts:
                fp.write('v %f %f %f\n' % (v[0], v[1], v[2]))

            for f in self.faces + 1:
                fp.write('f %d %d %d\n' % (f[0], f[1], f[2]))

    def forward(self, betas, pose, trans, simplify=False):
        """
              Construct a compute graph that takes in parameters and outputs a tensor as
              model vertices. Face indices are also returned as a numpy ndarray.

              Prameters:
              ---------
              pose: Also known as 'theta', a [24,3] tensor indicating child joint rotation
              relative to parent joint. For root joint it's global orientation.
              Represented in a axis-angle format.

              betas: Parameter for model shape. A tensor of shape [10] as coefficients of
              PCA components. Only 10 components were released by SMPL author.

              trans: Global translation tensor of shape [3].

              Return:
              ------
              A tensor for vertices, and a numpy ndarray as face indices.

        """
        id_to_col = {self.kintree_table[1, i]: i
                     for i in range(self.kintree_table.shape[1])}
        parent = {
            i: id_to_col[self.kintree_table[0, i]]
            for i in range(1, self.kintree_table.shape[1])
        }
        v_shaped = torch.tensordot(self.shapedirs, betas, dims=([2], [0])) + self.v_template
        J = torch.matmul(self.J_regressor, v_shaped)
        R_cube_big = self.rodrigues(pose.view(-1, 1, 3))

        if simplify:
            v_posed = v_shaped
        else:
            R_cube = R_cube_big[1:]
            I_cube = (torch.eye(3, dtype=torch.float64).unsqueeze(dim=0) + \
                      torch.zeros((R_cube.shape[0], 3, 3), dtype=torch.float64)).to(self.device)
            lrotmin = torch.reshape(R_cube - I_cube, (-1, 1)).squeeze()
            v_posed = v_shaped + torch.tensordot(self.posedirs, lrotmin, dims=([2], [0]))

        results = []
        results.append(
            self.with_zeros(torch.cat((R_cube_big[0], torch.reshape(J[0, :], (3, 1))), dim=1))
        )
        for i in range(1, self.kintree_table.shape[1]):
            results.append(
                torch.matmul(
                    results[parent[i]],
                    self.with_zeros(
                        torch.cat(
                            (R_cube_big[i], torch.reshape(J[i, :] - J[parent[i], :], (3, 1))),
                            dim=1
                        )
                    )
                )
            )

        stacked = torch.stack(results, dim=0)
        results = stacked - \
                  self.pack(
                      torch.matmul(
                          stacked,
                          torch.reshape(
                              torch.cat((J, torch.zeros((24, 1), dtype=torch.float64).to(self.device)), dim=1),
                              (24, 4, 1)
                          )
                      )
                  )
        T = torch.tensordot(self.weights, results, dims=([1], [0]))
        rest_shape_h = torch.cat(
            (v_posed, torch.ones((v_posed.shape[0], 1), dtype=torch.float64).to(self.device)), dim=1
        )
        v = torch.matmul(T, torch.reshape(rest_shape_h, (-1, 4, 1)))
        v = torch.reshape(v, (-1, 4))[:, :3]
        result = v + torch.reshape(trans, (1, 3))
        return result

def adjust_bboxes_to_image_border(boxes, image_shape, threshold=20):
    '''Adjust bounding boxes to stick to image border if they are within a certain threshold.
    Args:
    boxes: (n, 4)
    image_shape: (height, width)
    threshold: pixel threshold
    Returns:
    adjusted_boxes: adjusted bounding boxes
    '''

    # Image dimensions
    h, w = image_shape

    # Adjust boxes
    boxes[:, 0] = torch.where(boxes[:, 0] < threshold, torch.tensor(
        0, dtype=torch.float, device=boxes.device), boxes[:, 0])  # x1
    boxes[:, 1] = torch.where(boxes[:, 1] < threshold, torch.tensor(
        0, dtype=torch.float, device=boxes.device), boxes[:, 1])  # y1
    boxes[:, 2] = torch.where(boxes[:, 2] > w - threshold, torch.tensor(
        w, dtype=torch.float, device=boxes.device), boxes[:, 2])  # x2
    boxes[:, 3] = torch.where(boxes[:, 3] > h - threshold, torch.tensor(
        h, dtype=torch.float, device=boxes.device), boxes[:, 3])  # y2

    return boxes
def bbox_iou(box1, boxes, iou_thres=0.9, image_shape=(640, 640), raw_output=False):
    '''Compute the Intersection-Over-Union of a bounding box with respect to an array of other bounding boxes.
    Args:
    box1: (4, )
    boxes: (n, 4)
    Returns:
    high_iou_indices: Indices of boxes with IoU > thres
    '''
    boxes = adjust_bboxes_to_image_border(boxes, image_shape)
    # obtain coordinates for intersections
    x1 = torch.max(box1[0], boxes[:, 0])
    y1 = torch.max(box1[1], boxes[:, 1])
    x2 = torch.min(box1[2], boxes[:, 2])
    y2 = torch.min(box1[3], boxes[:, 3])

    # compute the area of intersection
    intersection = (x2 - x1).clamp(0) * (y2 - y1).clamp(0)

    # compute the area of both individual boxes
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])

    # compute the area of union
    union = box1_area + box2_area - intersection

    # compute the IoU
    iou = intersection / union  # Should be shape (n, )
    if raw_output:
        if iou.numel() == 0:
            return 0
        return iou

    # get indices of boxes with IoU > thres
    high_iou_indices = torch.nonzero(iou > iou_thres).flatten()

    return high_iou_indices
class Judgement:
    def __init__(self):  # 统一配置项
        self.token = None
        self.post_header = {
            "Host": "api.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/121.0.0.0 Safari/537.36",
            "Cookie": "",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.bilibili.com",
            "Referer": "https://www.bilibili.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }
        self.get_header = {
            "Cookie": "",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/121.0.0.0 Safari/537.36",
            "Accept": "application/json, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }
        self.csrf = None

def big_vip_sign():
    sign_url = "https://api.bilibili.com/pgc/activity/score/task/sign"
    payload = {
        "csrf": judge.csrf,
    }
    sign_result = judge.post_data(url=sign_url, data=payload)
    logging.info("大会员签到成功！")


sign_status = True
if not judge.cookies_login():
    sign_status = judge.QR_login()
if sign_status:
    big_vip_sign()
    while True:
        try:
            judge_id = get_next_judge()
            print(judge_id)
            case_type = get_judge_info(case_id=judge_id)
            vote(vote_num=0, case_id=judge_id)
            if case_type in [1, 3]:
                vote(vote_num=1, case_id=judge_id)
            if case_type in [2, 4]:
                vote(vote_num=11, case_id=judge_id)
            time.sleep(random.randint(5, 10))
        except TypeError:
            logging.info("任务结束或中断！")
            sys.exit()
else:
    logging.error("用户未登录或登录失败，任务结束！")

def vote(vote_num=0, case_id=None):
    vote_url = "https://api.bilibili.com/x/credit/v2/jury/vote"
    payload = {
        "case_id": str(case_id),
        "vote": vote_num,
        "insiders": 0,
        "anonymous": 0,
        "content": "",
        "csrf": judge.csrf,
    }
    vote_result = judge.post_data(url=vote_url, data=payload)
    logging.info("案件" + case_id + "投票成功！")


class MyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.input_tip = None
        self.course = None
        self.grid_layout = None
        self.weights = None
        self.button_close = None
        self.button_calculate = None
        self.result_label = None
        self.button_create = None
        self.row_input = None
        self.layout = None
        self.inputs = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("均分计算")
        self.layout = QVBoxLayout()

        self.input_tip = QLabel("请输入科目数")
        self.layout.addWidget(self.input_tip)

        self.row_input = QLineEdit()
        self.layout.addWidget(self.row_input)

        self.button_create = QPushButton("创建科目")
        self.button_create.clicked.connect(self.create_inputs)
        self.layout.addWidget(self.button_create)

        self.result_label = QLabel()
        self.layout.addWidget(self.result_label)

        self.button_calculate = QPushButton("计算均分")
        self.button_calculate.clicked.connect(self.calculate_weighted_average)

        self.button_close = QPushButton("关闭")
        self.button_close.clicked.connect(self.close)

        self.setLayout(self.layout)

    def create_inputs(self):
        rows = int(self.row_input.text())
        self.inputs = []
        self.course = []
        self.weights = []
        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(QLabel("科目"), 0, 0)
        self.grid_layout.addWidget(QLabel("成绩"), 0, 1)
        self.grid_layout.addWidget(QLabel("学分"), 0, 2)
        for row in range(1, rows + 1):
            input_course = QLineEdit()
            self.grid_layout.addWidget(input_course, row, 0)
            self.course.append(input_course)

            input_array = QLineEdit()
            self.grid_layout.addWidget(input_array, row, 1)
            self.inputs.append(input_array)

            input_weight = QLineEdit()
            self.grid_layout.addWidget(input_weight, row, 2)
            self.weights.append(input_weight)

        self.layout.addLayout(self.grid_layout)
        self.layout.addWidget(self.button_close)
        self.layout.addWidget(self.button_calculate)

    def calculate_weighted_average(self):
        total_weight = 0
        weighted_sum = 0
        for i, input_array in enumerate(self.inputs):
            try:
                value = float(input_array.text())
                weight = float(self.weights[i].text())
                total_weight += weight
                weighted_sum += value * weight
            except ValueError:
                pass

        if total_weight != 0:
            average = weighted_sum / total_weight
            self.result_label.setText(f"均分：{average}")
        else:
            self.result_label.setText("无法计算均分")
        font = QFont()
        font.setPointSize(30)
        self.result_label.setFont(font)
        self.save_detail()

    def save_detail(self):
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        with open(file="./log.txt", mode="a+", encoding="UTF-8") as f:
            f.write("******************************************************************" + "\n")
            f.write(str(current_time) + "\n")
            for i, input_array in enumerate(self.inputs):
                try:
                    f.write(f"科目："
                            + str(self.course[i].text())
                            + f" ,成绩："
                            + str(input_array.text())
                            + f" ,学分："
                            + str(self.weights[i].text())
                            + "\n")
                except ValueError:
                    pass
            f.write(str(self.result_label.text()) + "\n")
            f.write("******************************************************************" + "\n")
            f.close()

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def mode(self):
        return sqrt(self.x ** 2 + self.y ** 2)


result = {"x": [], "y": []}
num = 3331
df = pd.read_excel("point12.xlsx", sheet_name="Sheet1")
points = []
points_new = []
for i in range(0, num):
    points.append(Point(df.values[i][1], df.values[i][2]))
for point in points:
    new = Point(
        x=(point.x * sqrt((point.x - 100/sqrt(point.x**2+point.y**2)*point.x)**2+(point.y - 100/sqrt(point.x**2 + point.y**2)*point.y)**2)/sqrt(point.x**2 + point.y**2)),
        y=(point.y * sqrt((point.x - 100/sqrt(point.x**2+point.y**2)*point.x)**2+(point.y - 100/sqrt(point.x**2 + point.y**2)*point.y)**2)/sqrt(point.x**2 + point.y**2)))
    points_new.append(new)
ooow = []
for i in range(0, len(points_new)):
    if sqrt(points_new[i].x**2+points_new[i].y**2) <= 350:
        ooow.append(points_new[i])
for oo in ooow:
    result["x"].append(oo.x)
    result["y"].append(oo.y)
df1 = pd.DataFrame(result)
df1.to_excel("123.xlsx")

def objective_function(x):
    mirror_width = x[0]
    install_height = x[1]

    # 根据镜面宽度和安装高度计算镜面数量和总面积
    mirror_num = len(position_data)
    mirror_area = mirror_num * mirror_width * mirror_height

    # 计算单位镜面积年平均输出热功率
    output_power = calculate_output_power(mirror_area, efficiency)

    abs_diff = np.abs(output_power - 60)  # 根据问题3，额定功率为60MW
    return abs_diff


# 参数范围
bounds = [mirror_width_range, install_height_range]

# 调用优化算法求解
result = differential_evolution(objective_function, bounds)
optimal_params = result.x  # 最优参数

# 将结果保存到result3.xlsx文件中
df_result = pd.DataFrame({'Mirror Width': [optimal_params[0]],
                          'Install Height': [optimal_params[1]],
                          'Abs_Difference': [result.fun]})

with pd.ExcelWriter('result3.xlsx') as writer:
    df_result.to_excel(writer, sheet_name='Sheet1', index=False)

def objective_function(x):
    mirror_width = x[0]
    install_height = x[1]

    # 根据镜面宽度和安装高度计算镜面数量和总面积
    mirror_num = len(position_data)
    mirror_area = mirror_num * mirror_width * mirror_height

    # 计算单位镜面积年平均输出热功率
    output_power = calculate_output_power(mirror_area, efficiency)

    abs_diff = np.abs(output_power - 60)  # 根据问题3，额定功率为60MW
    return abs_diff


# 参数范围
bounds = [mirror_width_range, install_height_range]

# 调用优化算法求解
result = differential_evolution(objective_function, bounds)
optimal_params = result.x  # 最优参数

# 将结果保存到result3.xlsx文件中
df_result = pd.DataFrame({'Mirror Width': [optimal_params[0]],
                          'Install Height': [optimal_params[1]],
                          'Abs_Difference': [result.fun]})

with pd.ExcelWriter('result3.xlsx') as writer:
    df_result.to_excel(writer, sheet_name='Sheet1', index=False)

def draw(RGB_data, address, choose):
    RGB_color = ["red", "green", "blue"]
    pic, ax = plt.subplots(1, 1, figsize=(16, 9))
    ax.set_ylim(0, 2800)
    ax.set_yticks(range(0, 2801, 400))
    for _ in range(3):
        test = RGB_data[_]
        ax.plot(range(3300), test, color=RGB_color[_])
    if choose:
        plt.show()
    else:
        plt.savefig(address)
class Dijkstra:
    def __init__(self, graph, start, goal):
        self.graph = graph      # 邻接表
        self.start = start      # 起点
        self.goal = goal        # 终点

        self.open_list = {}     # open 表
        self.closed_list = {}   # closed 表

        self.open_list[start] = 0.0     # 将起点放入 open_list 中

        self.parent = {start: None}     # 存储节点的父子关系。键为子节点，值为父节点。方便做最后路径的回溯
        self.min_dis = None             # 最短路径的长度

    def shortest_path(self):

        while True:
            if self.open_list is None:
                print('搜索失败， 结束！')
                break
            distance, min_node = min(zip(self.open_list.values(), self.open_list.keys()))      # 取出距离最小的节点
            self.open_list.pop(min_node)                                                       # 将其从 open_list 中去除

            self.closed_list[min_node] = distance                  # 将节点加入 closed_list 中

            if min_node == self.goal:                              # 如果节点为终点
                self.min_dis = distance
                shortest_path = [self.goal]                        # 记录从终点回溯的路径
                father_node = self.parent[self.goal]
                while father_node != self.start:
                    shortest_path.append(father_node)
                    father_node = self.parent[father_node]
                shortest_path.append(self.start)
                print(shortest_path[::-1])                         # 逆序
                print('最短路径的长度为：{}'.format(self.min_dis))
                print('找到最短路径， 结束！')
                return shortest_path[::-1], self.min_dis			# 返回最短路径和最短路径长度

            for node in self.graph[min_node].keys():               # 遍历当前节点的邻接节点
                if node not in self.closed_list.keys():            # 邻接节点不在 closed_list 中
                    if node in self.open_list.keys():              # 如果节点在 open_list 中
                        if self.graph[min_node][node] + distance < self.open_list[node]:
                            self.open_list[node] = distance + self.graph[min_node][node]         # 更新节点的值
                            self.parent[node] = min_node           # 更新继承关系
                    else:                                          # 如果节点不在 open_list 中
                        self.open_list[node] = distance + self.graph[min_node][node]             # 计算节点的值，并加入 open_list 中
                        self.parent[node] = min_node               # 更新继承关系

class Dijkstra:
    def __init__(self, graph, start, goal):
        self.graph = graph      # 邻接表
        self.start = start      # 起点
        self.goal = goal        # 终点

        self.open_list = {}     # open 表
        self.closed_list = {}   # closed 表

        self.open_list[start] = 0.0     # 将起点放入 open_list 中

        self.parent = {start: None}     # 存储节点的父子关系。键为子节点，值为父节点。方便做最后路径的回溯
        self.min_dis = None             # 最短路径的长度

    def shortest_path(self):

        while True:
            if self.open_list is None:
                print('搜索失败， 结束！')
                break
            distance, min_node = min(zip(self.open_list.values(), self.open_list.keys()))      # 取出距离最小的节点
            self.open_list.pop(min_node)                                                       # 将其从 open_list 中去除

            self.closed_list[min_node] = distance                  # 将节点加入 closed_list 中

            if min_node == self.goal:                              # 如果节点为终点
                self.min_dis = distance
                shortest_path = [self.goal]                        # 记录从终点回溯的路径
                father_node = self.parent[self.goal]
                while father_node != self.start:
                    shortest_path.append(father_node)
                    father_node = self.parent[father_node]
                shortest_path.append(self.start)
                print(shortest_path[::-1])                         # 逆序
                print('最短路径的长度为：{}'.format(self.min_dis))
                print('找到最短路径， 结束！')
                return shortest_path[::-1], self.min_dis			# 返回最短路径和最短路径长度

            for node in self.graph[min_node].keys():               # 遍历当前节点的邻接节点
                if node not in self.closed_list.keys():            # 邻接节点不在 closed_list 中
                    if node in self.open_list.keys():              # 如果节点在 open_list 中
                        if self.graph[min_node][node] + distance < self.open_list[node]:
                            self.open_list[node] = distance + self.graph[min_node][node]         # 更新节点的值
                            self.parent[node] = min_node           # 更新继承关系
                    else:                                          # 如果节点不在 open_list 中
                        self.open_list[node] = distance + self.graph[min_node][node]             # 计算节点的值，并加入 open_list 中
                        self.parent[node] = min_node               # 更新继承关系

class Music_search(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.get_music
        logger.info("[Music]载入成功")

    def get_url(self, name_or_id, mode):
        request_url = ""
        if mode == "search":
            request_url = "https://music.penguinway.space/search?keywords=" + str(name_or_id)
        if mode == "get":
            request_url = "https://music.penguinway.space/song/url/v1?id=" + str(name_or_id) + "&level=exhigh"
        re = requests.get(url=request_url)
        return re.json()

    def clear_file(self, data, re):
        max_len = 30
        songs = []
        if len(data) > max_len:
            songs = [song for song in data if not song["did"]]
            re += "\n已清理多余音乐！"
            logger.info("已清理多余音乐！")
            logger.info(str(songs))
        else:
            songs = data
        return songs, re

    def get_music(self, e_context: EventContext):
        if e_context["context"].type != ContextType.TEXT:
            return
        string = e_context["context"].content
        reply = Reply()
        reply.type = ReplyType.TEXT
        msg: ChatMessage = e_context["context"]["msg"]

        if "音乐查询%" in string or "查询音乐%" in string:
            names = string[5:]
            if names == "":
                reply.content = "音乐名为空！请输入正确的音乐名！\n"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
            results_search = self.get_url(name_or_id=names, mode="search")
            logger.info("查询音乐:" + str(names))
            music_id = results_search["result"]["songs"][0]["id"]
            result_get = self.get_url(name_or_id=music_id, mode="get")
            music_url = result_get["data"][0]["url"]
            logger.info("播放链接:" + str(music_url))
            reply.content = ("\n作品名:" + str(results_search["result"]["songs"][0]["name"]) +
                             "\n作者名:" + str(results_search["result"]["songs"][0]["artists"][0]["name"]) +
                             "\n播放链接:" + music_url)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS

        elif "添加音乐%" in string or "音乐添加%" in string:
            names = string[5:]
            if names == "":
                reply.content = "音乐名为空！请输入正确的音乐名！\n"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
            with open("/chatgpt-on-wechat/plugins/music_url/music.json", mode="r", encoding="UTF-8") as f:
                file = json.load(f)
            results = self.get_url(name_or_id=names, mode="search")
            logger.info("添加音乐:" + str(names))
            json_file = {
                "id": str(results["result"]["songs"][0]["id"]),
                "作品名": str(results["result"]["songs"][0]["name"]),
                "作者名": str(results["result"]["songs"][0]["artists"][0]["name"]),
                "did": False
            }
            file.append(json_file)
            with open("/chatgpt-on-wechat/plugins/music_url/music.json", mode="w", encoding="UTF-8") as f:
                json.dump(file, f, indent=4, ensure_ascii=False)
            logger.info("添加音乐到json文件中成功")
            reply.content = ("添加成功！\n作品名："
                             + str(json_file["作品名"])
                             + "\n作者名："
                             + str(json_file["作者名"]))
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS

        elif "%音乐日推" == string or "%日推音乐" == string:
            with open("/chatgpt-on-wechat/plugins/music_url/music.json", mode="r", encoding="UTF-8") as f:
                song = json.load(f)
            if song[-1]["did"]:
                reply.content = "列表中已经没有歌曲可以推荐，请添加！"
                logger.info("列表为空！退出！")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
            for today_song in song:
                if not today_song["did"]:
                    music_id = today_song["id"]
                    result = self.get_url(name_or_id=music_id, mode="get")
                    music_url = result["data"][0]["url"]
                    today_song["did"] = True
                    reply.content = ("今日日推:" +
                                     "\n作品名：" + str(today_song["作品名"]) +
                                     "\n作者名：" + str(today_song["作者名"]) +
                                     "\n播放链接：" + str(music_url)
                                     )
                    break
                else:
                    continue
            songs, reply.content = self.clear_file(data=song, re=reply.content)
            e_context["reply"] = reply
            with open("/chatgpt-on-wechat/plugins/music_url/music.json", mode="w", encoding="UTF-8") as f:
                json.dump(songs, f, indent=4, ensure_ascii=False)
            e_context.action = EventAction.BREAK_PASS

        elif "%查询日推" == string or "%日推查询" == string:
            with open("/chatgpt-on-wechat/plugins/music_url/music.json", mode="r", encoding="UTF-8") as f:
                song = json.load(f)
                reply.content = "日推列表为:\n"
            for i in range(0, len(song)):
                reply.content += (
                        str(i + 1) + ":"
                        + song[i]["作品名"]
                        + "    "
                        + "播放情况:" + str(song[i]["did"]) + "\n")
            songs, reply.content = self.clear_file(data=song, re=reply.content)
            with open("/chatgpt-on-wechat/plugins/music_url/music.json", mode="w", encoding="UTF-8") as f:
                json.dump(songs, f, indent=4, ensure_ascii=False)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS

        elif "删除音乐%" in string or "音乐删除%" in string:
            name = string[5:]
            with open("/chatgpt-on-wechat/plugins/music_url/music.json", mode="r", encoding="UTF-8") as f:
                file = json.load(f)
            if not name.isdigit():
                for i in range(0, len(file)):
                    if name == file[i]["作品名"]:
                        del file[i]
                        logger.info("删除列表项")
                        reply.content = "删除成功！"
                        break
                    if i == len(file):
                        reply.content = "查无此曲！"
            elif name.isdigit():
                del file[name]
                logger.info("删除列表项")
                reply.content = "删除成功！"
            else:
                reply.content = "请输入正确的作品名！"
            with open("/chatgpt-on-wechat/plugins/music_url/music.json", mode="w", encoding="UTF-8") as f:
                json.dump(file, f, indent=4, ensure_ascii=False)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
        else:
            e_context.action = EventAction.CONTINUE

    def get_help_text(self, **kwargs):
        help_text = ("使用说明：\n" + "1.查询音乐 命令为: 查询音乐%example or 音乐查询%example\n" +
                     "2.添加音乐到日推列表 命令为: 添加音乐%example or 音乐添加%example\n" +
                     "3.日推 命令为: %音乐日推 or %日推音乐 (Tip.一般不建议手动进行日推)\n" +
                     "4.查询日推 命令为: %查询日推 or %日推查询\n" +
                     "5.删除列表项 命令为: 删除音乐%example or 音乐删除%example (Tip.[example]可为作品名或序号)")
        return help_text

def song_send():
    song = []
    with open("music.json", mode="r", encoding="UTF-8") as f:
        song = json.load(f)
    for i in range(0, len(song)):
        if not song[i]["did"]:
            today_song = song[i]
            music_id = today_song["id"]
            url_url = "https://music.penguinway.space/song/url/v1?id=" + str(music_id) + "&level=exhigh"
            geturl = requests.get(url=url_url)
            result = geturl.json()
            music_url = result["data"][0]["url"]
            today_song["did"] = True
            print("今日日推：\n" +
                  "作品名：" + str(today_song["作品名"]) + "\n" +
                  "作者名：" + str(today_song["作者名"]) + "\n" +
                  "播放链接：" + str(music_url)
                  )
            with open("music.json", mode="w", encoding="UTF-8") as f:
                json.dump(song, f, indent=4, ensure_ascii=False)
            break
        else:
            continue

def song_send():
    song = []
    with open("music.json", mode="r", encoding="UTF-8") as f:
        song = json.load(f)
    for i in range(0, len(song)):
        if not song[i]["did"]:
            today_song = song[i]
            music_id = today_song["id"]
            url_url = "https://music.penguinway.space/song/url/v1?id=" + str(music_id) + "&level=exhigh"
            geturl = requests.get(url=url_url)
            result = geturl.json()
            music_url = result["data"][0]["url"]
            today_song["did"] = True
            print("今日日推：\n" +
                  "作品名：" + str(today_song["作品名"]) + "\n" +
                  "作者名：" + str(today_song["作者名"]) + "\n" +
                  "播放链接：" + str(music_url)
                  )
            with open("music.json", mode="w", encoding="UTF-8") as f:
                json.dump(song, f, indent=4, ensure_ascii=False)
            break
        else:
            continue

def abs_val(num: float) -> float:
    """
    Find the absolute value of a number.

    >>> abs_val(-5.1)
    5.1
    >>> abs_val(-5) == abs_val(5)
    True
    >>> abs_val(0)
    0
    """
    return -num if num < 0 else num

def abs_min(x: list[int]) -> int:
    """
    >>> abs_min([0,5,1,11])
    0
    >>> abs_min([3,-10,-2])
    -2
    >>> abs_min([])
    Traceback (most recent call last):
        ...
    ValueError: abs_min() arg is an empty sequence
    """
    if len(x) == 0:
        raise ValueError("abs_min() arg is an empty sequence")
    j = x[0]
    for i in x:
        if abs_val(i) < abs_val(j):
            j = i
    return j

def abs_max(x: list[int]) -> int:
    """
    >>> abs_max([0,5,1,11])
    11
    >>> abs_max([3,-10,-2])
    -10
    >>> abs_max([])
    Traceback (most recent call last):
        ...
    ValueError: abs_max() arg is an empty sequence
    """
    if len(x) == 0:
        raise ValueError("abs_max() arg is an empty sequence")
    j = x[0]
    for i in x:
        if abs(i) > abs(j):
            j = i
    return j

def abs_max_sort(x: list[int]) -> int:
    """
    >>> abs_max_sort([0,5,1,11])
    11
    >>> abs_max_sort([3,-10,-2])
    -10
    >>> abs_max_sort([])
    Traceback (most recent call last):
        ...
    ValueError: abs_max_sort() arg is an empty sequence
    """
    if len(x) == 0:
        raise ValueError("abs_max_sort() arg is an empty sequence")
    return sorted(x, key=abs)[-1]

def add(first: int, second: int) -> int:
    """
    Implementation of addition of integer

    Examples:
    >>> add(3, 5)
    8
    >>> add(13, 5)
    18
    >>> add(-7, 2)
    -5
    >>> add(0, -7)
    -7
    >>> add(-321, 0)
    -321
    """
    while second != 0:
        c = first & second
        first ^= second
        second = c << 1
    return first

def aliquot_sum(input_num: int) -> int:
    """
    Finds the aliquot sum of an input integer, where the
    aliquot sum of a number n is defined as the sum of all
    natural numbers less than n that divide n evenly. For
    example, the aliquot sum of 15 is 1 + 3 + 5 = 9. This is
    a simple O(n) implementation.
    @param input_num: a positive integer whose aliquot sum is to be found
    @return: the aliquot sum of input_num, if input_num is positive.
    Otherwise, raise a ValueError
    Wikipedia Explanation: https://en.wikipedia.org/wiki/Aliquot_sum

    >>> aliquot_sum(15)
    9
    >>> aliquot_sum(6)
    6
    >>> aliquot_sum(-1)
    Traceback (most recent call last):
      ...
    ValueError: Input must be positive
    >>> aliquot_sum(0)
    Traceback (most recent call last):
      ...
    ValueError: Input must be positive
    >>> aliquot_sum(1.6)
    Traceback (most recent call last):
      ...
    ValueError: Input must be an integer
    >>> aliquot_sum(12)
    16
    >>> aliquot_sum(1)
    0
    >>> aliquot_sum(19)
    1
    """
    if not isinstance(input_num, int):
        raise ValueError("Input must be an integer")
    if input_num <= 0:
        raise ValueError("Input must be positive")
    return sum(
        divisor for divisor in range(1, input_num // 2 + 1) if input_num % divisor == 0
    )

def surface_area_cube(side_length: float) -> float:
    """
    Calculate the Surface Area of a Cube.

    >>> surface_area_cube(1)
    6
    >>> surface_area_cube(1.6)
    15.360000000000003
    >>> surface_area_cube(0)
    0
    >>> surface_area_cube(3)
    54
    >>> surface_area_cube(-1)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cube() only accepts non-negative values
    """
    if side_length < 0:
        raise ValueError("surface_area_cube() only accepts non-negative values")
    return 6 * side_length**2

def surface_area_cuboid(length: float, breadth: float, height: float) -> float:
    """
    Calculate the Surface Area of a Cuboid.

    >>> surface_area_cuboid(1, 2, 3)
    22
    >>> surface_area_cuboid(0, 0, 0)
    0
    >>> surface_area_cuboid(1.6, 2.6, 3.6)
    38.56
    >>> surface_area_cuboid(-1, 2, 3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cuboid() only accepts non-negative values
    >>> surface_area_cuboid(1, -2, 3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cuboid() only accepts non-negative values
    >>> surface_area_cuboid(1, 2, -3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cuboid() only accepts non-negative values
    """
    if length < 0 or breadth < 0 or height < 0:
        raise ValueError("surface_area_cuboid() only accepts non-negative values")
    return 2 * ((length * breadth) + (breadth * height) + (length * height))

def surface_area_sphere(radius: float) -> float:
    """
    Calculate the Surface Area of a Sphere.
    Wikipedia reference: https://en.wikipedia.org/wiki/Sphere
    Formula: 4 * pi * r^2

    >>> surface_area_sphere(5)
    314.1592653589793
    >>> surface_area_sphere(1)
    12.566370614359172
    >>> surface_area_sphere(1.6)
    32.169908772759484
    >>> surface_area_sphere(0)
    0.0
    >>> surface_area_sphere(-1)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_sphere() only accepts non-negative values
    """
    if radius < 0:
        raise ValueError("surface_area_sphere() only accepts non-negative values")
    return 4 * pi * radius**2

def surface_area_hemisphere(radius: float) -> float:
    """
    Calculate the Surface Area of a Hemisphere.
    Formula: 3 * pi * r^2

    >>> surface_area_hemisphere(5)
    235.61944901923448
    >>> surface_area_hemisphere(1)
    9.42477796076938
    >>> surface_area_hemisphere(0)
    0.0
    >>> surface_area_hemisphere(1.1)
    11.40398133253095
    >>> surface_area_hemisphere(-1)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_hemisphere() only accepts non-negative values
    """
    if radius < 0:
        raise ValueError("surface_area_hemisphere() only accepts non-negative values")
    return 3 * pi * radius**2

def surface_area_cone(radius: float, height: float) -> float:
    """
    Calculate the Surface Area of a Cone.
    Wikipedia reference: https://en.wikipedia.org/wiki/Cone
    Formula: pi * r * (r + (h ** 2 + r ** 2) ** 0.5)

    >>> surface_area_cone(10, 24)
    1130.9733552923256
    >>> surface_area_cone(6, 8)
    301.59289474462014
    >>> surface_area_cone(1.6, 2.6)
    23.387862992395807
    >>> surface_area_cone(0, 0)
    0.0
    >>> surface_area_cone(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cone() only accepts non-negative values
    >>> surface_area_cone(1, -2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cone() only accepts non-negative values
    >>> surface_area_cone(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cone() only accepts non-negative values
    """
    if radius < 0 or height < 0:
        raise ValueError("surface_area_cone() only accepts non-negative values")
    return pi * radius * (radius + (height**2 + radius**2) ** 0.5)

def surface_area_conical_frustum(
    radius_1: float, radius_2: float, height: float
) -> float:
    """
    Calculate the Surface Area of a Conical Frustum.

    >>> surface_area_conical_frustum(1, 2, 3)
    45.511728065337266
    >>> surface_area_conical_frustum(4, 5, 6)
    300.7913575056268
    >>> surface_area_conical_frustum(0, 0, 0)
    0.0
    >>> surface_area_conical_frustum(1.6, 2.6, 3.6)
    78.57907060751548
    >>> surface_area_conical_frustum(-1, 2, 3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_conical_frustum() only accepts non-negative values
    >>> surface_area_conical_frustum(1, -2, 3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_conical_frustum() only accepts non-negative values
    >>> surface_area_conical_frustum(1, 2, -3)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_conical_frustum() only accepts non-negative values
    """
    if radius_1 < 0 or radius_2 < 0 or height < 0:
        raise ValueError(
            "surface_area_conical_frustum() only accepts non-negative values"
        )
    slant_height = (height**2 + (radius_1 - radius_2) ** 2) ** 0.5
    return pi * ((slant_height * (radius_1 + radius_2)) + radius_1**2 + radius_2**2)

def surface_area_cylinder(radius: float, height: float) -> float:
    """
    Calculate the Surface Area of a Cylinder.
    Wikipedia reference: https://en.wikipedia.org/wiki/Cylinder
    Formula: 2 * pi * r * (h + r)

    >>> surface_area_cylinder(7, 10)
    747.6990515543707
    >>> surface_area_cylinder(1.6, 2.6)
    42.22300526424682
    >>> surface_area_cylinder(0, 0)
    0.0
    >>> surface_area_cylinder(6, 8)
    527.7875658030853
    >>> surface_area_cylinder(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cylinder() only accepts non-negative values
    >>> surface_area_cylinder(1, -2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cylinder() only accepts non-negative values
    >>> surface_area_cylinder(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_cylinder() only accepts non-negative values
    """
    if radius < 0 or height < 0:
        raise ValueError("surface_area_cylinder() only accepts non-negative values")
    return 2 * pi * radius * (height + radius)

def surface_area_torus(torus_radius: float, tube_radius: float) -> float:
    """Calculate the Area of a Torus.
    Wikipedia reference: https://en.wikipedia.org/wiki/Torus
    :return 4pi^2 * torus_radius * tube_radius
    >>> surface_area_torus(1, 1)
    39.47841760435743
    >>> surface_area_torus(4, 3)
    473.7410112522892
    >>> surface_area_torus(3, 4)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_torus() does not support spindle or self intersecting tori
    >>> surface_area_torus(1.6, 1.6)
    101.06474906715503
    >>> surface_area_torus(0, 0)
    0.0
    >>> surface_area_torus(-1, 1)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_torus() only accepts non-negative values
    >>> surface_area_torus(1, -1)
    Traceback (most recent call last):
        ...
    ValueError: surface_area_torus() only accepts non-negative values
    """
    if torus_radius < 0 or tube_radius < 0:
        raise ValueError("surface_area_torus() only accepts non-negative values")
    if torus_radius < tube_radius:
        raise ValueError(
            "surface_area_torus() does not support spindle or self intersecting tori"
        )
    return 4 * pow(pi, 2) * torus_radius * tube_radius

def area_square(side_length: float) -> float:
    """
    Calculate the area of a square.

    >>> area_square(10)
    100
    >>> area_square(0)
    0
    >>> area_square(1.6)
    2.5600000000000005
    >>> area_square(-1)
    Traceback (most recent call last):
        ...
    ValueError: area_square() only accepts non-negative values
    """
    if side_length < 0:
        raise ValueError("area_square() only accepts non-negative values")
    return side_length**2

def area_triangle(base: float, height: float) -> float:
    """
    Calculate the area of a triangle given the base and height.

    >>> area_triangle(10, 10)
    50.0
    >>> area_triangle(1.6, 2.6)
    2.08
    >>> area_triangle(0, 0)
    0.0
    >>> area_triangle(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_triangle() only accepts non-negative values
    >>> area_triangle(1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_triangle() only accepts non-negative values
    >>> area_triangle(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: area_triangle() only accepts non-negative values
    """
    if base < 0 or height < 0:
        raise ValueError("area_triangle() only accepts non-negative values")
    return (base * height) / 2

def area_triangle_three_sides(side1: float, side2: float, side3: float) -> float:
    """
    Calculate area of triangle when the length of 3 sides are known.
    This function uses Heron's formula: https://en.wikipedia.org/wiki/Heron%27s_formula

    >>> area_triangle_three_sides(5, 12, 13)
    30.0
    >>> area_triangle_three_sides(10, 11, 12)
    51.521233486786784
    >>> area_triangle_three_sides(0, 0, 0)
    0.0
    >>> area_triangle_three_sides(1.6, 2.6, 3.6)
    1.8703742940919619
    >>> area_triangle_three_sides(-1, -2, -1)
    Traceback (most recent call last):
        ...
    ValueError: area_triangle_three_sides() only accepts non-negative values
    >>> area_triangle_three_sides(1, -2, 1)
    Traceback (most recent call last):
        ...
    ValueError: area_triangle_three_sides() only accepts non-negative values
    >>> area_triangle_three_sides(2, 4, 7)
    Traceback (most recent call last):
        ...
    ValueError: Given three sides do not form a triangle
    >>> area_triangle_three_sides(2, 7, 4)
    Traceback (most recent call last):
        ...
    ValueError: Given three sides do not form a triangle
    >>> area_triangle_three_sides(7, 2, 4)
    Traceback (most recent call last):
        ...
    ValueError: Given three sides do not form a triangle
    """
    if side1 < 0 or side2 < 0 or side3 < 0:
        raise ValueError("area_triangle_three_sides() only accepts non-negative values")
    elif side1 + side2 < side3 or side1 + side3 < side2 or side2 + side3 < side1:
        raise ValueError("Given three sides do not form a triangle")
    semi_perimeter = (side1 + side2 + side3) / 2
    area = sqrt(
        semi_perimeter
        * (semi_perimeter - side1)
        * (semi_perimeter - side2)
        * (semi_perimeter - side3)
    )
    return area

def area_parallelogram(base: float, height: float) -> float:
    """
    Calculate the area of a parallelogram.

    >>> area_parallelogram(10, 20)
    200
    >>> area_parallelogram(1.6, 2.6)
    4.16
    >>> area_parallelogram(0, 0)
    0
    >>> area_parallelogram(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_parallelogram() only accepts non-negative values
    >>> area_parallelogram(1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_parallelogram() only accepts non-negative values
    >>> area_parallelogram(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: area_parallelogram() only accepts non-negative values
    """
    if base < 0 or height < 0:
        raise ValueError("area_parallelogram() only accepts non-negative values")
    return base * height

def area_trapezium(base1: float, base2: float, height: float) -> float:
    """
    Calculate the area of a trapezium.

    >>> area_trapezium(10, 20, 30)
    450.0
    >>> area_trapezium(1.6, 2.6, 3.6)
    7.5600000000000005
    >>> area_trapezium(0, 0, 0)
    0.0
    >>> area_trapezium(-1, -2, -3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(-1, 2, 3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(1, -2, 3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(1, 2, -3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(-1, -2, 3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(1, -2, -3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    >>> area_trapezium(-1, 2, -3)
    Traceback (most recent call last):
        ...
    ValueError: area_trapezium() only accepts non-negative values
    """
    if base1 < 0 or base2 < 0 or height < 0:
        raise ValueError("area_trapezium() only accepts non-negative values")
    return 1 / 2 * (base1 + base2) * height

def area_circle(radius: float) -> float:
    """
    Calculate the area of a circle.

    >>> area_circle(20)
    1256.6370614359173
    >>> area_circle(1.6)
    8.042477193189871
    >>> area_circle(0)
    0.0
    >>> area_circle(-1)
    Traceback (most recent call last):
        ...
    ValueError: area_circle() only accepts non-negative values
    """
    if radius < 0:
        raise ValueError("area_circle() only accepts non-negative values")
    return pi * radius**2

def area_ellipse(radius_x: float, radius_y: float) -> float:
    """
    Calculate the area of a ellipse.

    >>> area_ellipse(10, 10)
    314.1592653589793
    >>> area_ellipse(10, 20)
    628.3185307179587
    >>> area_ellipse(0, 0)
    0.0
    >>> area_ellipse(1.6, 2.6)
    13.06902543893354
    >>> area_ellipse(-10, 20)
    Traceback (most recent call last):
        ...
    ValueError: area_ellipse() only accepts non-negative values
    >>> area_ellipse(10, -20)
    Traceback (most recent call last):
        ...
    ValueError: area_ellipse() only accepts non-negative values
    >>> area_ellipse(-10, -20)
    Traceback (most recent call last):
        ...
    ValueError: area_ellipse() only accepts non-negative values
    """
    if radius_x < 0 or radius_y < 0:
        raise ValueError("area_ellipse() only accepts non-negative values")
    return pi * radius_x * radius_y

def area_rhombus(diagonal_1: float, diagonal_2: float) -> float:
    """
    Calculate the area of a rhombus.

    >>> area_rhombus(10, 20)
    100.0
    >>> area_rhombus(1.6, 2.6)
    2.08
    >>> area_rhombus(0, 0)
    0.0
    >>> area_rhombus(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_rhombus() only accepts non-negative values
    >>> area_rhombus(1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_rhombus() only accepts non-negative values
    >>> area_rhombus(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: area_rhombus() only accepts non-negative values
    """
    if diagonal_1 < 0 or diagonal_2 < 0:
        raise ValueError("area_rhombus() only accepts non-negative values")
    return 1 / 2 * diagonal_1 * diagonal_2

def area_reg_polygon(sides: int, length: float) -> float:
    """
    Calculate the area of a regular polygon.
    Wikipedia reference: https://en.wikipedia.org/wiki/Polygon#Regular_polygons
    Formula: (n*s^2*cot(pi/n))/4

    >>> area_reg_polygon(3, 10)
    43.301270189221945
    >>> area_reg_polygon(4, 10)
    100.00000000000001
    >>> area_reg_polygon(0, 0)
    Traceback (most recent call last):
        ...
    ValueError: area_reg_polygon() only accepts integers greater than or equal to \
three as number of sides
    >>> area_reg_polygon(-1, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_reg_polygon() only accepts integers greater than or equal to \
three as number of sides
    >>> area_reg_polygon(5, -2)
    Traceback (most recent call last):
        ...
    ValueError: area_reg_polygon() only accepts non-negative values as \
length of a side
    >>> area_reg_polygon(-1, 2)
    Traceback (most recent call last):
        ...
    ValueError: area_reg_polygon() only accepts integers greater than or equal to \
three as number of sides
    """
    if not isinstance(sides, int) or sides < 3:
        raise ValueError(
            "area_reg_polygon() only accepts integers greater than or \
equal to three as number of sides"
        )
    elif length < 0:
        raise ValueError(
            "area_reg_polygon() only accepts non-negative values as \
length of a side"
        )
    return (sides * length**2) / (4 * tan(pi / sides))
    return (sides * length**2) / (4 * tan(pi / sides))

def trapezoidal_area(
    fnc: Callable[[float], float],
    x_start: float,
    x_end: float,
    steps: int = 100,
) -> float:
    """
    Treats curve as a collection of linear lines and sums the area of the
    trapezium shape they form
    :param fnc: a function which defines a curve
    :param x_start: left end point to indicate the start of line segment
    :param x_end: right end point to indicate end of line segment
    :param steps: an accuracy gauge; more steps increases the accuracy
    :return: a float representing the length of the curve

    >>> def f(x):
    ...    return 5
    >>> f"{trapezoidal_area(f, 12.0, 14.0, 1000):.3f}"
    '10.000'
    >>> def f(x):
    ...    return 9*x**2
    >>> f"{trapezoidal_area(f, -4.0, 0, 10000):.4f}"
    '192.0000'
    >>> f"{trapezoidal_area(f, -4.0, 4.0, 10000):.4f}"
    '384.0000'
    """
    x1 = x_start
    fx1 = fnc(x_start)
    area = 0.0
    for _ in range(steps):
        # Approximates small segments of curve as linear and solve
        # for trapezoidal area
        x2 = (x_end - x_start) / steps + x1
        fx2 = fnc(x2)
        area += abs(fx2 + fx1) * (x2 - x1) / 2
        # Increment step
        x1 = x2
        fx1 = fx2
    return area

def average_absolute_deviation(nums: list[int]) -> float:
    """
    Return the average absolute deviation of a list of numbers.
    Wiki: https://en.wikipedia.org/wiki/Average_absolute_deviation

    >>> average_absolute_deviation([0])
    0.0
    >>> average_absolute_deviation([4, 1, 3, 2])
    1.0
    >>> average_absolute_deviation([2, 70, 6, 50, 20, 8, 4, 0])
    20.0
    >>> average_absolute_deviation([-20, 0, 30, 15])
    16.25
    >>> average_absolute_deviation([])
    Traceback (most recent call last):
        ...
    ValueError: List is empty
    """
    if not nums:  # Makes sure that the list is not empty
        raise ValueError("List is empty")

    average = sum(nums) / len(nums)  # Calculate the average
    return sum(abs(x - average) for x in nums) / len(nums)

def mean(nums: list) -> float:
    """
    Find mean of a list of numbers.
    Wiki: https://en.wikipedia.org/wiki/Mean

    >>> mean([3, 6, 9, 12, 15, 18, 21])
    12.0
    >>> mean([5, 10, 15, 20, 25, 30, 35])
    20.0
    >>> mean([1, 2, 3, 4, 5, 6, 7, 8])
    4.5
    >>> mean([])
    Traceback (most recent call last):
        ...
    ValueError: List is empty
    """
    if not nums:
        raise ValueError("List is empty")
    return sum(nums) / len(nums)

def median(nums: list) -> int | float:
    """
    Find median of a list of numbers.
    Wiki: https://en.wikipedia.org/wiki/Median

    >>> median([0])
    0
    >>> median([4, 1, 3, 2])
    2.5
    >>> median([2, 70, 6, 50, 20, 8, 4])
    8

    Args:
        nums: List of nums

    Returns:
        Median.
    """
    # The sorted function returns list[SupportsRichComparisonT@sorted]
    # which does not support `+`
    sorted_list: list[int] = sorted(nums)
    length = len(sorted_list)
    mid_index = length >> 1
    return (
        (sorted_list[mid_index] + sorted_list[mid_index - 1]) / 2
        if length % 2 == 0
        else sorted_list[mid_index]
    )

def mode(input_list: list) -> list[Any]:
    """This function returns the mode(Mode as in the measures of
    central tendency) of the input data.

    The input list may contain any Datastructure or any Datatype.

    >>> mode([2, 3, 4, 5, 3, 4, 2, 5, 2, 2, 4, 2, 2, 2])
    [2]
    >>> mode([3, 4, 5, 3, 4, 2, 5, 2, 2, 4, 4, 2, 2, 2])
    [2]
    >>> mode([3, 4, 5, 3, 4, 2, 5, 2, 2, 4, 4, 4, 2, 2, 4, 2])
    [2, 4]
    >>> mode(["x", "y", "y", "z"])
    ['y']
    >>> mode(["x", "x" , "y", "y", "z"])
    ['x', 'y']
    """
    if not input_list:
        return []
    result = [input_list.count(value) for value in input_list]
    y = max(result)  # Gets the maximum count in the input list.
    # Gets values of modes
    return sorted({input_list[i] for i, value in enumerate(result) if value == y})

def bailey_borwein_plouffe(digit_position: int, precision: int = 1000) -> str:
    """
    Implement a popular pi-digit-extraction algorithm known as the
    Bailey-Borwein-Plouffe (BBP) formula to calculate the nth hex digit of pi.
    Wikipedia page:
    https://en.wikipedia.org/wiki/Bailey%E2%80%93Borwein%E2%80%93Plouffe_formula
    @param digit_position: a positive integer representing the position of the digit to
    extract.
    The digit immediately after the decimal point is located at position 1.
    @param precision: number of terms in the second summation to calculate.
    A higher number reduces the chance of an error but increases the runtime.
    @return: a hexadecimal digit representing the digit at the nth position
    in pi's decimal expansion.

    >>> "".join(bailey_borwein_plouffe(i) for i in range(1, 11))
    '243f6a8885'
    >>> bailey_borwein_plouffe(5, 10000)
    '6'
    >>> bailey_borwein_plouffe(-10)
    Traceback (most recent call last):
      ...
    ValueError: Digit position must be a positive integer
    >>> bailey_borwein_plouffe(0)
    Traceback (most recent call last):
      ...
    ValueError: Digit position must be a positive integer
    >>> bailey_borwein_plouffe(1.7)
    Traceback (most recent call last):
      ...
    ValueError: Digit position must be a positive integer
    >>> bailey_borwein_plouffe(2, -10)
    Traceback (most recent call last):
      ...
    ValueError: Precision must be a nonnegative integer
    >>> bailey_borwein_plouffe(2, 1.6)
    Traceback (most recent call last):
      ...
    ValueError: Precision must be a nonnegative integer
    """
    if (not isinstance(digit_position, int)) or (digit_position <= 0):
        raise ValueError("Digit position must be a positive integer")
    elif (not isinstance(precision, int)) or (precision < 0):
        raise ValueError("Precision must be a nonnegative integer")

    # compute an approximation of (16 ** (n - 1)) * pi whose fractional part is mostly
    # accurate
    sum_result = (
        4 * _subsum(digit_position, 1, precision)
        - 2 * _subsum(digit_position, 4, precision)
        - _subsum(digit_position, 5, precision)
        - _subsum(digit_position, 6, precision)
    )

    # return the first hex digit of the fractional part of the result
    return hex(int((sum_result % 1) * 16))[2:]

def _subsum(
    digit_pos_to_extract: int, denominator_addend: int, precision: int
) -> float:
    # only care about first digit of fractional part; don't need decimal
    """
    Private helper function to implement the summation
    functionality.
    @param digit_pos_to_extract: digit position to extract
    @param denominator_addend: added to denominator of fractions in the formula
    @param precision: same as precision in main function
    @return: floating-point number whose integer part is not important
    """
    total = 0.0
    for sum_index in range(digit_pos_to_extract + precision):
        denominator = 8 * sum_index + denominator_addend
        if sum_index < digit_pos_to_extract:
            # if the exponential term is an integer and we mod it by the denominator
            # before dividing, only the integer part of the sum will change;
            # the fractional part will not
            exponential_term = pow(
                16, digit_pos_to_extract - 1 - sum_index, denominator
            )
        else:
            exponential_term = pow(16, digit_pos_to_extract - 1 - sum_index)
        total += exponential_term / denominator
    return total

def decimal_to_negative_base_2(num: int) -> int:
    """
    This function returns the number negative base 2
        of the decimal number of the input data.

    Args:
        int: The decimal number to convert.

    Returns:
        int: The negative base 2 number.

    Examples:
        >>> decimal_to_negative_base_2(0)
        0
        >>> decimal_to_negative_base_2(-19)
        111101
        >>> decimal_to_negative_base_2(4)
        100
        >>> decimal_to_negative_base_2(7)
        11011
    """
    if num == 0:
        return 0
    ans = ""
    while num != 0:
        num, rem = divmod(num, -2)
        if rem < 0:
            rem += 2
            num += 1
        ans = str(rem) + ans
    return int(ans)

def prime_factors(n: int) -> list:
    """Find Prime Factors.
    >>> prime_factors(100)
    [2, 2, 5, 5]
    >>> prime_factors(0)
    Traceback (most recent call last):
        ...
    ValueError: Only positive integers have prime factors
    >>> prime_factors(-10)
    Traceback (most recent call last):
        ...
    ValueError: Only positive integers have prime factors
    """
    if n <= 0:
        raise ValueError("Only positive integers have prime factors")
    pf = []
    while n % 2 == 0:
        pf.append(2)
        n = int(n / 2)
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        while n % i == 0:
            pf.append(i)
            n = int(n / i)
    if n > 2:
        pf.append(n)
    return pf

def number_of_divisors(n: int) -> int:
    """Calculate Number of Divisors of an Integer.
    >>> number_of_divisors(100)
    9
    >>> number_of_divisors(0)
    Traceback (most recent call last):
        ...
    ValueError: Only positive numbers are accepted
    >>> number_of_divisors(-10)
    Traceback (most recent call last):
        ...
    ValueError: Only positive numbers are accepted
    """
    if n <= 0:
        raise ValueError("Only positive numbers are accepted")
    div = 1
    temp = 1
    while n % 2 == 0:
        temp += 1
        n = int(n / 2)
    div *= temp
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        temp = 1
        while n % i == 0:
            temp += 1
            n = int(n / i)
        div *= temp
    if n > 1:
        div *= 2
    return div

def euler_phi(n: int) -> int:
    """Calculate Euler's Phi Function.
    >>> euler_phi(100)
    40
    >>> euler_phi(0)
    Traceback (most recent call last):
        ...
    ValueError: Only positive numbers are accepted
    >>> euler_phi(-10)
    Traceback (most recent call last):
        ...
    ValueError: Only positive numbers are accepted
    """
    if n <= 0:
        raise ValueError("Only positive numbers are accepted")
    s = n
    for x in set(prime_factors(n)):
        s *= (x - 1) / x
    return int(s)


def binary_exp_recursive(base: float, exponent: int) -> float:
    """
    Computes a^b recursively, where a is the base and b is the exponent

    >>> binary_exp_recursive(3, 5)
    243
    >>> binary_exp_recursive(11, 13)
    34522712143931
    >>> binary_exp_recursive(-1, 3)
    -1
    >>> binary_exp_recursive(0, 5)
    0
    >>> binary_exp_recursive(3, 1)
    3
    >>> binary_exp_recursive(3, 0)
    1
    >>> binary_exp_recursive(1.5, 4)
    5.0625
    >>> binary_exp_recursive(3, -1)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")

    if exponent == 0:
        return 1

    if exponent % 2 == 1:
        return binary_exp_recursive(base, exponent - 1) * base

    b = binary_exp_recursive(base, exponent // 2)
    return b * b


def binary_exp_iterative(base: float, exponent: int) -> float:
    """
    Computes a^b iteratively, where a is the base and b is the exponent

    >>> binary_exp_iterative(3, 5)
    243
    >>> binary_exp_iterative(11, 13)
    34522712143931
    >>> binary_exp_iterative(-1, 3)
    -1
    >>> binary_exp_iterative(0, 5)
    0
    >>> binary_exp_iterative(3, 1)
    3
    >>> binary_exp_iterative(3, 0)
    1
    >>> binary_exp_iterative(1.5, 4)
    5.0625
    >>> binary_exp_iterative(3, -1)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")

    res: int | float = 1
    while exponent > 0:
        if exponent & 1:
            res *= base

        base *= base
        exponent >>= 1

    return res

def binary_exp_mod_recursive(base: float, exponent: int, modulus: int) -> float:
    """
    Computes a^b % c recursively, where a is the base, b is the exponent, and c is the
    modulus

    >>> binary_exp_mod_recursive(3, 4, 5)
    1
    >>> binary_exp_mod_recursive(11, 13, 7)
    4
    >>> binary_exp_mod_recursive(1.5, 4, 3)
    2.0625
    >>> binary_exp_mod_recursive(7, -1, 10)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    >>> binary_exp_mod_recursive(7, 13, 0)
    Traceback (most recent call last):
        ...
    ValueError: Modulus must be a positive integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")
    if modulus <= 0:
        raise ValueError("Modulus must be a positive integer")

    if exponent == 0:
        return 1

    if exponent % 2 == 1:
        return (binary_exp_mod_recursive(base, exponent - 1, modulus) * base) % modulus

    r = binary_exp_mod_recursive(base, exponent // 2, modulus)
    return (r * r) % modulus

def binary_exp_mod_iterative(base: float, exponent: int, modulus: int) -> float:
    """
    Computes a^b % c iteratively, where a is the base, b is the exponent, and c is the
    modulus

    >>> binary_exp_mod_iterative(3, 4, 5)
    1
    >>> binary_exp_mod_iterative(11, 13, 7)
    4
    >>> binary_exp_mod_iterative(1.5, 4, 3)
    2.0625
    >>> binary_exp_mod_iterative(7, -1, 10)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    >>> binary_exp_mod_iterative(7, 13, 0)
    Traceback (most recent call last):
        ...
    ValueError: Modulus must be a positive integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")
    if modulus <= 0:
        raise ValueError("Modulus must be a positive integer")

    res: int | float = 1
    while exponent > 0:
        if exponent & 1:
            res = ((res % modulus) * (base % modulus)) % modulus

        base *= base
        exponent >>= 1

    return res

def binary_multiply(a: int, b: int) -> int:
    """
    Multiply 'a' and 'b' using bitwise multiplication.

    Parameters:
    a (int): The first number.
    b (int): The second number.

    Returns:
    int: a * b

    Examples:
    >>> binary_multiply(2, 3)
    6
    >>> binary_multiply(5, 0)
    0
    >>> binary_multiply(3, 4)
    12
    >>> binary_multiply(10, 5)
    50
    >>> binary_multiply(0, 5)
    0
    >>> binary_multiply(2, 1)
    2
    >>> binary_multiply(1, 10)
    10
    """
    res = 0
    while b > 0:
        if b & 1:
            res += a

        a += a
        b >>= 1

    return res

def binary_mod_multiply(a: int, b: int, modulus: int) -> int:
    """
    Calculate (a * b) % c using binary multiplication and modular arithmetic.

    Parameters:
    a (int): The first number.
    b (int): The second number.
    modulus (int): The modulus.

    Returns:
    int: (a * b) % modulus.

    Examples:
    >>> binary_mod_multiply(2, 3, 5)
    1
    >>> binary_mod_multiply(5, 0, 7)
    0
    >>> binary_mod_multiply(3, 4, 6)
    0
    >>> binary_mod_multiply(10, 5, 13)
    11
    >>> binary_mod_multiply(2, 1, 5)
    2
    >>> binary_mod_multiply(1, 10, 3)
    1
    """
    res = 0
    while b > 0:
        if b & 1:
            res = ((res % modulus) + (a % modulus)) % modulus

        a += a
        b >>= 1

    return res

def binomial_coefficient(n: int, r: int) -> int:
    """
    Find binomial coefficient using Pascal's triangle.

    Calculate C(n, r) using Pascal's triangle.

    :param n: The total number of items.
    :param r: The number of items to choose.
    :return: The binomial coefficient C(n, r).

    >>> binomial_coefficient(10, 5)
    252
    >>> binomial_coefficient(10, 0)
    1
    >>> binomial_coefficient(0, 10)
    1
    >>> binomial_coefficient(10, 10)
    1
    >>> binomial_coefficient(5, 2)
    10
    >>> binomial_coefficient(5, 6)
    0
    >>> binomial_coefficient(3, 5)
    0
    >>> binomial_coefficient(-2, 3)
    Traceback (most recent call last):
        ...
    ValueError: n and r must be non-negative integers
    >>> binomial_coefficient(5, -1)
    Traceback (most recent call last):
        ...
    ValueError: n and r must be non-negative integers
    >>> binomial_coefficient(10.1, 5)
    Traceback (most recent call last):
        ...
    TypeError: 'float' object cannot be interpreted as an integer
    >>> binomial_coefficient(10, 5.1)
    Traceback (most recent call last):
        ...
    TypeError: 'float' object cannot be interpreted as an integer
    """
    if n < 0 or r < 0:
        raise ValueError("n and r must be non-negative integers")
    if 0 in (n, r):
        return 1
    c = [0 for i in range(r + 1)]
    # nc0 = 1
    c[0] = 1
    for i in range(1, n + 1):
        # to compute current row from previous row.
        j = min(i, r)
        while j > 0:
            c[j] += c[j - 1]
            j -= 1
    return c[r]

def binomial_distribution(successes: int, trials: int, prob: float) -> float:
    """
    Return probability of k successes out of n tries, with p probability for one
    success

    The function uses the factorial function in order to calculate the binomial
    coefficient

    >>> binomial_distribution(3, 5, 0.7)
    0.30870000000000003
    >>> binomial_distribution (2, 4, 0.5)
    0.375
    """
    if successes > trials:
        raise ValueError("""successes must be lower or equal to trials""")
    if trials < 0 or successes < 0:
        raise ValueError("the function is defined for non-negative integers")
    if not isinstance(successes, int) or not isinstance(trials, int):
        raise ValueError("the function is defined for non-negative integers")
    if not 0 < prob < 1:
        raise ValueError("prob has to be in range of 1 - 0")
    probability = (prob**successes) * ((1 - prob) ** (trials - successes))
    # Calculate the binomial coefficient: n! / k!(n-k)!
    coefficient = float(factorial(trials))
    coefficient /= factorial(successes) * factorial(trials - successes)
    return probability * coefficient


def ceil(x: float) -> int:
    """
    Return the ceiling of x as an Integral.

    :param x: the number
    :return: the smallest integer >= x.

    >>> import math
    >>> all(ceil(n) == math.ceil(n) for n
    ...     in (1, -1, 0, -0, 1.1, -1.1, 1.0, -1.0, 1_000_000_000))
    True
    """
    return int(x) if x - int(x) <= 0 else int(x) + 1



