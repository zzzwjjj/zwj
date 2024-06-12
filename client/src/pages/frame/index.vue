<template>
    <div class="common-layout">
        <el-container>
            <el-header class="header-container">
                <span><img src="../../assets/login_3.png" width="40px" height="40px"></span>
                <h2 @click="titleClickBtn" >基于深度学习的软件故障预测与定位系统</h2>
                <div class="item">
                    <div class="help">
                        <el-dropdown>
                        <span class="help_inner">
                           <span>帮助</span>
                           <el-icon class="el-icon--righ icon">
                               <QuestionFilled/>
                           </el-icon>
                        </span>
                        <template #dropdown>
                            <el-dropdown-menu>
                                <el-dropdown-item @click="forgetPasswordBtn"
                                    >联系管理员</el-dropdown-item
                                >
                                <el-dropdown-item @click="downloadDocument"
                                    >下载使用文档</el-dropdown-item
                                >
                            </el-dropdown-menu>
                        </template>
                    </el-dropdown>
                    </div>
                    <el-avatar
                        src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png"
                    />
                    <el-dropdown @command="handleCommand">
                        <span>
                            {{ username }}，您好
                            <el-icon class="el-icon--right">
                                <arrow-down />
                            </el-icon>
                        </span>
                        <template #dropdown>
                            <el-dropdown-menu>
                                <el-dropdown-item command="edituserinfo"
                                    >修改个人信息</el-dropdown-item
                                >
                                <el-dropdown-item command="edituserinfo1"
                                    >修改密码</el-dropdown-item
                                >
                                <el-dropdown-item command="quit"
                                    >退出</el-dropdown-item
                                >
                            </el-dropdown-menu>
                        </template>
                    </el-dropdown>
                    <el-dialog v-model="dialogShow" width="20%" style="height: 450px" title="修改用户信息">
                        <template #default>
                            <div ref="visualizationRef" element-loading-text="生成中...">
                                <el-form :model="form" label-width="100px" label-position="top" style="width:80%;margin:30px auto 0 auto;">
                                    <el-form-item label="用户名:">
                                        <el-input v-model="form.username" />
                                    </el-form-item>
                                    <el-form-item label="昵称:">
                                        <el-input v-model="form.nickname" />
                                    </el-form-item>
<!--                                    <el-form-item label="密码:">-->
<!--                                        <el-input v-model="form.password"  />-->
<!--                                    </el-form-item>-->
                                    <el-form-item>
                                        <el-button type="primary" style="display: block;margin:0 auto;" @click="onSubmit">确认</el-button>
                                    </el-form-item>
                                </el-form>
                            </div>
                        </template>
                    </el-dialog>
                    <el-dialog v-model="dialogVisible" width="20%" style="height: 450px" title="修改密码">
                        <template #default>
                            <div ref="visualizationRef" element-loading-text="生成中...">
                                <el-form :model="registerForm" label-width="100px" label-position="top" style="width:80%;margin:30px auto 0 auto;">
                                    <el-form-item label="密码:">
                                        <el-input v-model="registerForm.password" />
                                    </el-form-item>
                                    <el-form-item label="确认密码:">
                                        <el-input v-model="registerForm.re_password"  />
                                    </el-form-item>
                                    <el-form-item>
                                        <el-button type="primary" style="display: block;margin:0 auto;" @click="onSubmit1">确认</el-button>
                                    </el-form-item>
                                </el-form>
                            </div>
                        </template>
                    </el-dialog>
                </div>
            </el-header>
            <el-container>
                <el-aside width="200px">
                    <el-menu
                        :default-active="store.state.modifyNavigation"
                        class="el-menu-vertical-demo"
                        router
                    >
                        <div class="user-info-container" style="background-color: #4877ee !important;">
                           <div class="user-avatar">
                             <el-avatar src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png"></el-avatar>
                           </div>
                           <div class="username">
                              {{ username }}
                           </div>
                        </div>

                        <el-menu-item index="/welcome"
                            ><el-icon><el-icon-pie-chart/></el-icon
                            >首页</el-menu-item
                        >
                        <el-menu-item index="/fault_location"
                            ><el-icon><el-icon-paperclip /></el-icon
                            >故障预测</el-menu-item
                        >
                        <el-menu-item index="/prop_map"
                            ><el-icon><Location /></el-icon
                            >故障定位</el-menu-item
                        >
                        <el-menu-item index="/Function_calls"
                            ><el-icon><el-icon-takeaway-box /></el-icon
                            >函数调用图</el-menu-item
                        >
                        <el-menu-item index="/fault_prop"
                            ><el-icon><DataAnalysis /></el-icon
                            >故障传播图</el-menu-item
                        >
<!--                        <el-menu-item index="/analysis"-->
<!--                            ><el-icon><Search /></el-icon>查询统计</el-menu-item-->
<!--                        >-->
                        <el-menu-item index="/code_manage"
                            ><el-icon><FolderOpened /></el-icon
                            >代码管理</el-menu-item
                        >
                        <el-menu-item index="/history"
                            ><el-icon><el-icon-search /></el-icon
                            >查询统计</el-menu-item
                        >
                        <el-menu-item index="/system"
                            ><el-icon><Notebook /></el-icon
                            >操作日志</el-menu-item
                        >
                        <el-menu-item v-if="form.is_superuser" index="/user"
                            ><el-icon><User /></el-icon
                            >用户管理</el-menu-item
                        >
<!--                        <el-menu-item v-if="form.is_superuser" index="/fileManage"-->
<!--                            ><el-icon><FolderOpened /></el-icon-->
<!--                            >文件管理</el-menu-item-->
<!--                        >-->
                    </el-menu>
                </el-aside>
                <el-main>
                    <!-- 二级路由展示 -->
                    <el-card>
                        <template #header>
                            <div>
                                <el-breadcrumb separator="/">
                                    <el-breadcrumb-item
                                        :to="{ path: '/welcome' }"
                                        >首页</el-breadcrumb-item
                                    >
                                    <el-breadcrumb-item>{{
                                        store.state.modifyNavigation
                                    }}</el-breadcrumb-item>
                                </el-breadcrumb>
                            </div>
                        </template>
                        <router-view />
                    </el-card>
                </el-main>
           </el-container>    <!-- 左侧导航栏-->
        </el-container>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import {Register, UserInfo} from "@/apis/auth";
import store from "@/store";
import {setUpdate, setUserUpdate,setpassword} from "@/apis/user";

const registerForm = reactive({
  user_id:"",
  password:"",
  re_password: "",
});
const router = useRouter();
const username = ref(null);
const dialogShow = ref(false);
const dialogVisible= ref(false);
const form = reactive({
      user_id:"",
      username: '',
      nickname: '',
      is_superuser: false
  })
const handleCommand = (command) => {
    if (command == "quit") {
        logout()
    }
    if(command == "edituserinfo"){
        dialogShow.value = true;
    }
    if(command == "edituserinfo1"){
        dialogVisible.value = true;
    }
};

const logout = () => {
    store.commit("paramsReset", {
            key: "userName",
            value: null,
        });
        store.commit("paramsReset", {
            key: "accessJwt",
            value: null,
        });
        ElMessage({
            message: "退出成功",
            type: "success",
            duration: 1500,
            onClose: () => {
                router.push({
                    name: "LoginPage",
                });
            },
        });
}
const onSubmit = () => {
    let {user_id,...otherForm} = form
    let query = {
        ...otherForm
    }
    setUpdate(user_id,query).then((res) => {
        const {status_code} = res;
        if (status_code == 20000) {
            ElMessage({
            message: `修改成功`,
            type: "success",
            duration: 1500,
            onClose: () => {
                dialogShow.value = false;
            },
            });
        }
        })
  }
const onSubmit1 = () => {
  if (registerForm.password != registerForm.re_password) {
    ElMessage({
      message: "两次密码输入不一致",
      type: "error",
      duration: 1500,
    });
    return;
  }
  let {user_id,...otherForm} = registerForm
  let query = {
      ...otherForm
  }
  setpassword(user_id,query).then((res) => {
      const {status_code} = res;
      if (status_code == 20000) {
          ElMessage({
          message: `修改成功`,
          type: "success",
          duration: 1500,
          onClose: () => {
              dialogVisible.value = false;
          },
          });
      }
      console.log(query.password)
      })
}
const getUserInfoData = async () => {
    UserInfo().then((res) => {
        const { status_code, msg, data } = res;
        if (status_code != 20000) {
            ElMessage({
                message: "身份信息获取失败,请重新登陆",
                type: "error",
                duration: 1500,
                onClose: () => {
                    router.push({
                        name: "LoginPage",
                    });
                },
            });
            return;
        } else {
            Object.keys(form).forEach((item) => {
                form[item] = data[item]
            })
            Object.keys(registerForm).forEach((item) => {
                registerForm[item] = data[item]
            })
            username.value = data.nickname;
            sessionStorage.setItem("userInfo",JSON.stringify(data))
            store.commit("paramsReset", {
                key: "userName",
                value: data.nickname,
            });
        }
    });
};

const initialization = async () => {
    const jwt = store.state.accessJwt;
    if (jwt == null || !jwt) {
        ElMessage({
            message: "身份信息获取失败!",
            type: "error",
            duration: 1500,
            onClose: () => {
                router.push({
                    name: "LoginPage",
                });
            },
        });
        return;
    }
    await getUserInfoData();
};
const titleClickBtn = () => {
    router.push({
        name: "IndexPage",
    });
};
onMounted(async () => {
    await initialization();
});
const forgetPasswordBtn = async () => {
  ElMessageBox.alert('联系管理员-1943944123@qq.com', '提示', {
    confirmButtonText: '好的',
  })
}

const downloadDocument = async () => {
  try {
    // 定义要下载的文件路径
    const filePath = '/shiyong.docx'; // 请更新为你的文件路径
    // 创建下载链接元素
    const downloadLink = document.createElement('a');
    downloadLink.href = filePath;
    downloadLink.download = 'shiyong.docx'; // 指定要下载的文件名
    // 触发点击下载链接的事件
    downloadLink.click();
    // 清理：等待1秒后从DOM中移除下载链接元素
    await new Promise(resolve => setTimeout(resolve, 1000));
    downloadLink.remove();
  } catch (error) {
    console.error('下载文档出错:', error);
  }
}



</script>

<style lang="scss">

//用户名导航栏显示
.el-menu-vertical-demo {
    display: flex;
    flex-direction: column;
    padding-top: 30px; /* 调整距离顶部的距离，给用户信息容器留出空间 */
}

.user-info-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: #4d58b5;
    padding: 20px;
    margin-bottom: 20px; /* 调整下边距，给其他菜单项留出空间 */
}

.user-avatar {
    margin-bottom: 10px;
}

.username {
    color: #ffffff;
    font-weight: bold;
    text-align: center;
}
.el-menu-item {
    transition: box-shadow 0.5s ease, transform 0.5s ease;
}
.el-menu-item:hover {
    background-color: #1d4fd2;
    box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.2); /* 添加阴影效果 */
    transform: translateY(-4px); /* 向上平移2像素 */
    transform: translateX(4px);
}
.header-container h2 {
   font-size:20px;
   display:inline-block;
   width: 400px;
}

  .el-header {
            //background: url("@/assets/banner.png") no-repeat center;
            background-color: #1d4fd2;
            position: relative;
            height: 70px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            h2 {
               position: absolute;
                margin: 20px 0;
                color: white;
                left: 80px;
                font-size: 22px;
            }
            .item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                .help{
                    width: 100px;
                    clear: both;
                    .help_inner{
                        display: block;
                        clear: both;
                        width: 100px;
                        position: relative;
                    }
                    .icon{
                       position: absolute;
                       margin: auto;
                       left: 0;
                       top: 0;
                       right: 20px;
                    }
                }
                .el-dropdown {
                    margin: 10px 0;
                    margin-left: 10px;
                    color: #fff;
                    .el-tooltip__trigger {
                        height: 100%;
                    }
                }
            }
        }
        .el-aside {
            min-height: 90vh;
            padding: 10px;
            .el-menu {
                border-radius: 1rem;
                height: 100%;
                background: #4877ee;
                .el-menu-item {
                    color: white;
                    height:57px
                }
            }
        }

        .header-container h2 {
          display: inline-block;
        }
        .el-main {
            min-height: 90vh;
            .el-card {
                height: 100%;
                border-radius: 1rem;
                .el-card__body {
                    height: 100%;
                }
            }
        }
</style>
<style lang="scss" scoped>
    ::v-deep {
        .item{
            .el-dialog{
                background: url("../../assets/1111.jpg") no-repeat 0 0;
                background-size: cover;
                border-radius: 20px;
                .el-dialog__header{
                    font-weight: 600;
                    text-align: center;
                    margin-top: 20px;
                    .el-dialog__title{
                        font-size: 24px!important;
                    }
                
                }
            }
            .el-form-item__label{
                font-weight: 600;
            }
            .el-input__wrapper,.el-select__wrapper{
                background: #eee!important;
                border-radius: 30px;
                border: 1px solid #333;
            }
        }

    }
</style>
