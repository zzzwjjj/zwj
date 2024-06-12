
<template>
  <el-card>
    <el-form
        :model="createProjectForm"
        :rules="createProjectFormRule"
        ref="createProjectFormRef"
    >
      <el-form-item
          label="上传代码"
          v-loading="uploadLoading"
          element-loading-text="上传中..."
      >
        <el-upload
            style="width: 100%"
            drag
            action=""
            :accept="acceptTypes"
            :show-file-list="false"
            :http-request="uploadToServer"
            multiple
        >
          <el-icon class="el-icon--upload">
            <upload-filled/>
          </el-icon>
          <div class="el-upload__text">
            把需要上传的文件拖拽到这里<em>点我上传</em>
          </div>
        </el-upload>
      </el-form-item>
    </el-form>

    <div style="display: flex; justify-content:center;  margin: 10px 0">
      <el-radio-group v-model="resultSelect">
        <el-radio
            v-for="(item, index) in resultSelectOption"
            :label="item.name"
            :value="index"
            :key="index"
            size="large"
            :disabled="item.is_op"
            @change="selectIficationChange"
            v-show="index <= 8 "
        >
          <span style="font-size: 18px;">{{ item.name }}</span>
        </el-radio>
      </el-radio-group>
    </div>
    <div style="display: flex; margin: 10px 0">
      <p style="font-size: 17px; margin-right: 10px; ">选择预测函数名:</p>
      <el-select
          v-model="selectResult"
          placeholder="请先选择上面的分类"
          size="medium"
          style="width: 240px"
          @change="selectResultChange"
      >
        <el-option
            v-for="item in resultInfoOptions"
            :key="item"
            :label="item"
            :value="item"
        />
      </el-select>
      <div class="submit-container">
      <el-button type="primary" @click="submitBtn(createProjectFormRef)" size="medium" style="margin-left:15px; margin-top: -20px;"
      >提交
      </el-button
      >
    </div>
    </div>



  </el-card>
</template>

<script setup>
import {ref, reactive} from "vue";
import {submitCode} from "@/apis/fault_location";
import {UploadFile} from "@/apis/upload_file";
import {useRouter} from "vue-router";
import {showCount} from "@/apis/count";
const router = useRouter();

const uploadLoading = ref(false);

const acceptTypes = ref(".py");
const createProjectFormRef = ref();
const selectResult = ref(null);

const resultSelect = ref(null);

const resultInfoOptions = reactive([]);

const selectIficationChange = async () => {
  resultInfoOptions.length = 0;
  for (let i in resultSelectOption[resultSelect.value].select_list) {
    resultInfoOptions.push(
        resultSelectOption[resultSelect.value].select_list[i]
    );
  }
};

const resultSelectOption = reactive({});



const resultSelectOptionReversName = reactive({
  1: "输入有效性和表示",
  2: "API滥用",
  3: "安全功能",
  4: "时间和状态",
  5: "错误",
  6: "代码质量",
  7: "封装",
  8: "环境",
});


const createProjectFormRule = reactive({
  name: [{required: true, message: "请输入题目", trigger: "blur"}],
});

const createProjectForm = reactive({
  name: null,
  upload_file: null,
  func_name: null,
});

const selectResultChange = async () => {
  createProjectForm.func_name = selectResult.value;
};

const submitBtn = async (createProjectFormRef) => {
      createProjectFormRef.validate((valid, field) => {
            if (valid) {
              if (!createProjectForm.upload_file) {
                ElMessage({
                  message: "请先上传代码.py文件",
                  type: "error",
                  duration: 1500,
                });
                return;
              }

              if (!selectResult.value) {
                ElMessage({
                  message: "请先选择分类",
                  type: "error",
                  duration: 1500,
                });
                return;
              }
              submitCode(JSON.stringify(createProjectForm)).then((res) => {
                    const {status_code, msg, data, result_set} = res;
                    console.log(result_set);
                    if (status_code != 20000) {
                      ElMessage({
                        message: msg,
                        type: "error",
                        duration: 1500,
                      });
                      return;
                    }
                    ElMessage({
                      message: "成功，正在分析",
                      type: "success",
                      duration: 1000,

                    });
                    showCount({
                      file_name:createProjectForm.upload_file,
                      error:resultSelectOptionReversName[resultSelect.value],
                      func_name:createProjectForm.func_name,
                      result_set:result_set,
                      func_graph:data
                    }).then(res=>{
                      console.log(typeof  res);
                      console.log(typeof  res.msg);
                      console.log(res.data);
                    });
                    let messageContent = '<div style="display: flex; flex-wrap: wrap;justify-content: center;">';
                    messageContent += '<div style="width: 100%; text-align: center;">可能导致函数 <span style="font-weight: bold; color: red;">' + createProjectForm.func_name + '</span> 发生故障的函数分别如下</div>';
                    result_set.forEach((item, index) => {
                      if(index<8){
                        if (index % 2 === 0 ) {
                        messageContent += '<div style="width: 50%; padding-left: 35px;">' +(index+1)+['.']+ item + '</div>';
                      } else {
                        messageContent += '<div style="width: 50%; padding-left: 35px;">' +(index+1)+['.']+ item + '</div><br>';
                      }
                      }

                    });

                    messageContent += '</div>';
                    ElMessageBox.alert('', '分析结果', {
                      confirmButtonText: 'OK',
                      dangerouslyUseHTMLString: true, // 允许在消息框中使用 HTML 字符串
                      message: messageContent

                    });
                  }
              )
              ;
            }
          }
      )
      ;
    }
;

const uploadToServer = (file) => {
  uploadLoading.value = true;
  const formData = new FormData();
  formData.append("file", file.file);
  UploadFile(formData).then((res) => {
    const {status_code, msg, data} = res;
    if (status_code != 20000) {
      ElMessage({
        message: msg,
        type: "error",
        duration: 1500,
        onClose: () => {
          uploadLoading.value = false;
        },
      });

      return;
    } else {
      createProjectForm.upload_file = data.file_name;
      resultSelectOption.length = 0;
      for (let index_id in data.select_data_op) {
        if (index_id === "0" || index_id === "9") {
          continue;
        }
        resultSelectOption[index_id] = {
          name: resultSelectOptionReversName[index_id],
          is_op: data.select_data_op[index_id].is_op,
          select_list: data.select_data_op[index_id].select_list,
        };
      }

      ElMessage({
        message: msg,
        type: "success",
        duration: 1500,
        onClose: () => {
          uploadLoading.value = false;
        },
      });
    }
  });
};
</script>

<style lang="scss">
  .submit-container {
    display: flex;
    justify-content: flex-end; /* 将按钮对齐到右侧 */
    margin-top: 20px; /* 添加一些顶部边距以进行分隔 */
  }

  /* 拖放区域的样式 */
  .el-upload__text {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100px; /* 根据需要调整高度 */
    border: 2px dashed #c0c4cc;
    border-radius: 5px;
    cursor: pointer;
  }

  .el-upload__text em {
    color: #409eff; /* 根据需要调整颜色 */
    cursor: pointer;
    margin-top: 5px; /* 在文本和强调之间添加一些间距 */
  }

  /* 单选按钮的样式 */
  .el-radio-group {
    display: flex;
    flex-wrap: wrap;
    margin-bottom: 10px; /* 添加一些底部边距以进行分隔 */
  }

  .el-radio {
    margin-right: 20px; /* 添加一些右边距以进行分隔 */
  }
</style>
