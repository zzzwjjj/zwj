<template>
<div class="background"></div>
  <div class="w-[100%] h-[100%] flex justify-center items-center" style="padding-top: 530px;background-image: url('./1.jpg')">
<!--    background-color:#b3c5f5-->
    <div class="container">
      <div class="form-box">
        <!-- 注册 -->
        <div class="register-box hidden">
          <h1 style="color:white ; font-size:25px">注册</h1>
          <input type="text" v-model="registerForm.username" placeholder="用户名"/>
          <input type="text" v-model="registerForm.nickname" placeholder="昵称"/>
          <input type="password" v-model="registerForm.password" placeholder="密码"/>
          <input type="password" v-model="registerForm.re_password" placeholder="确认密码"/>
          <button @click="RegisterSubmit">注册</button>
        </div>
        <!-- 登录 -->
        <div class="login-box">
          <h1 style="color:white ; font-size:25px">登录</h1>
          <form
              style="width: 100%;padding:0 0 ;display: flex;flex-wrap: wrap;align-items: center;justify-content: center;">
            <input style="width: 80%;" v-model="LoginForm.username" type="text" placeholder="用户名"/>
            <div
                style="width: 80%;position: relative;display: inline-block;border-bottom: 1px solid rgba(255,255,255,0.4);">
              <input :type="showPassword" placeholder="密码" v-model="LoginForm.password"
                     style="padding-right: 40px;border-bottom: none">
              <el-icon @click="showPasswordBtn" color="#fff"
                       style="position: absolute;right: 10px;top: 50%;transform: translateY(-50%)">
                <View/>
              </el-icon>
              </input>
            </div>
          </form>
          <button @click="LoginFunc">登录</button>
          <div style="margin-top: 30px;">
            <span @click="forgetPasswordBtn"
                  style="color: #fff;border-bottom: 1px solid rgba(255,255,255,0.4);">忘记密码</span>
          </div>
        </div>
      </div>
      <div class="con-box left" style="top">
        <h2><div>欢迎来到</div>
          <span class="titi">基于深度学习的</span></h2>
          <span class="tit">软件故障预测与定位系统</span>
        <p>快来试试<span>代码分析</span>吧</p>
        <img src="../../assets/login_2.jpg" alt=""/>
        <p>已有账号</p>
        <button id="login">去登录</button>
      </div>
      <div class="con-box right">
        <h2>
          <div>欢迎来到</div>
          <span class="titi">基于深度学习的</span></h2>
          <span class="tit">软件故障预测与定位系统</span>
        <p>快来试试<span>代码分析</span>吧</p>
        <img src="../../assets/login_2.jpg" alt=""/>
        <p>没有账号？</p>
        <button id="register">去注册</button>
      </div>
      <div style="padding-top: 98%; text-align: center;font-size: 16px;
font-weight: bold;
color: #000000;
text-shadow: 1px 0 #fff, -1px 0 #fff, 0 1px #fff, 0 -1px #fff;">
        <div>本系统可广泛应用于软件开发过程中的故障发现与处理</div>
        <div style="padding-top: 1%">©2024- 哈尔滨工程大学  管理员联系方式：1987654321 </div>
      </div>
    </div>
  </div>
<!--  </div >-->
</template>

<script setup>
import {ref, reactive, onMounted} from "vue";
import store from "@/store";
import {useRouter} from "vue-router";
import {Login, Register} from "@/apis/auth";

const router = useRouter();

const showRegister = ref(false);

const registerForm = reactive({
  username: null,
  password: null,
  re_password: null,
  nickname: null,
});
//  需要改
const LoginForm = reactive({
  username: "endpain",
  password: "123456",
});

const RegisterSubmit = async (registerFormRef) => {
  if (registerForm.password != registerForm.re_password) {
    ElMessage({
      message: "两次密码输入不一致",
      type: "error",
      duration: 1500,
    });
    return;
  }
  Register(JSON.stringify(registerForm)).then((res) => {
    const {status_code, msg, data} = res;
    if (status_code != 20000) {
      ElMessage({
        message: msg,
        type: "error",
        duration: 1500,
      });
      return;
    } else {
      ElMessage({
        message: `${msg},请登录吧！`,
        type: "success",
        duration: 1500,
        onClose: () => {
        },
      });
    }
  });
};

const LoginFunc = async () => {
  Login(JSON.stringify(LoginForm)).then(
      (res) => {
        store.commit("paramsReset", {
          key: "accessJwt",
          value: res.access,
        });
        ElMessage({
          message: "登陆成功!",
          type: "success",
          duration: 1500,
          onClose: () => {
            router.push({
              name: "IndexPage",
            });
          },
        });
      },
      (error) => {
        ElMessage({
          message: "登陆失败!账号或密码错误。请检查后重新输入",
          type: "error",
          duration: 1500,
          onClose: () => {
            // 清空账号密码输入框，需要重新输入
            loginFormRef.resetFields();
          },
        });
      }
  );
};

// 在新页面加载后自动刷新
window.onload = function() {
    // 导航到新页面
    window.location.href = "";
    // 刷新页面
    location.reload();
};

const RegisterFunc = async () => {
  for (let i in registerForm) {
    registerForm[i] = null;
  }
  showRegister.value = !showRegister.value;
};

onMounted(async () => {
  // 要操作到的元素
  let login = document.getElementById("login");
  let register = document.getElementById("register");
  let form_box = document.getElementsByClassName("form-box")[0];
  let register_box = document.getElementsByClassName("register-box")[0];
  let login_box = document.getElementsByClassName("login-box")[0];
  // 去注册按钮点击事件
  register.addEventListener("click", () => {
    form_box.style.transform = "translateX(103%)";
    login_box.classList.add("hidden");
    register_box.classList.remove("hidden");
  });
  // 去登录按钮点击事件
  login.addEventListener("click", () => {
    form_box.style.transform = "translateX(0%)";
    register_box.classList.add("hidden");
    login_box.classList.remove("hidden");
  });
});

const forgetPasswordBtn = async () => {
  ElMessageBox.alert('忘记密码请联系管理员-1943944123@qq.com', '提示', {
    confirmButtonText: '好的',
  })
}

const showPassword = ref('password')
const showPasswordBtn = async () => {
  if (showPassword.value == "password") {
    showPassword.value = 'text'
  } else {
    showPassword.value = 'password'
  }
}

</script>

<style lang="scss" scoped>
body #app {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  width: 100%;
  //padding-bottom: 100px;
}

.container {
  background-color: #fff;
  //background-color: #a0cfff;
  width: 650px;
  height: 450px;
  border-radius: 5px;
  /* 阴影 */
  box-shadow: 0px 0px 15px rgba(0, 0, 0, 0.3);
  /* 相对定位 */
  position: relative;
  bottom: 290px;
}

.form-box {
  /* 绝对定位 */
  position: absolute;
  top: -10%;
  //background-color: #d3b7d8;
  background-color: #4877ee;
  width: 320px;
  height: 530px;
  border-radius: 5px;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2;
  /* 动画过渡 加速后减速 */
  transition: 0.5s ease-in-out;
}

.register-box,
.login-box {
  /* 弹性布局 垂直排列 */
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.hidden {
  display: none;
  transition: 0.5s;
}

h1 {
  text-align: center;
  margin-bottom: 25px;
  /* 大写 */
  text-transform: uppercase;
  color: #fff;
  /* 字间距 */
  letter-spacing: 5px;
}

input {
  background-color: transparent;
  width: 80%;
  color: #fff;
  border: none;
  /* 下边框样式 */
  border-bottom: 1px solid rgba(255, 255, 255, 0.4);
  padding: 10px 0;
  text-indent: 10px;
  margin: 8px 0;
  font-size: 14px;
  letter-spacing: 2px;
}

input::placeholder {
  color: #fff;
}

input:focus {
  //color: #a262ad;
  color: #ffffff;
  outline: none;
  //border-bottom: 1px solid #a262ad80;
  border-bottom: 1px solid rgba(216, 225, 212, 0.5);
  transition: 0.5s;
}

input:focus::placeholder {
  opacity: 0;
}

.form-box button {
  width: 70%;
  margin-top: 35px;
  background-color: #f6f6f6;
  outline: none;
  border-radius: 8px;
  padding: 13px;
  //color: #a262ad;
  color: #1d4fd2;
  letter-spacing: 2px;
  border: none;
  cursor: pointer;
}

.form-box button:hover {
  //background-color: #a262ad;
  background-color: #c5d1ee;
  color: #1d4fd2;
  transition: background-color 0.5s ease;
}

.con-box {
  width: 50%;
  /* 弹性布局 垂直排列 居中 */
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  /* 绝对定位 居中 */
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
}

.con-box.left {
  left: 1%;
}

.con-box.right {
  right: 0%;
}

.con-box h2 {
  color: #8e9aaf;
  font-size: 25px;
  font-weight: bold;
  letter-spacing: 3px;
  text-align: center;
  margin-bottom: 4px;
}

.con-box p {
  font-size: 12px;
  letter-spacing: 2px;
  color: #8e9aaf;
  text-align: center;
}

.con-box span {
  //color: #d3b7d8;
  color: #1d4fd2;
}

.con-box img {
  width: 150px;
  height: 150px;
  opacity: 0.9;
  margin: 40px 0;
}

.con-box button {
  font-size: 20px;
  margin-top: 3%;
  background-color: #fff;
  //color: #a262ad;
  color: #1d4fd2;
  //border: 1px solid #d3b7d8;
  border: 1px solid #1d4fd2;
  padding: 6px 10px;
  border-radius: 5px;
  letter-spacing: 1px;
  outline: none;
  cursor: pointer;
}

.con-box left h2 span {
  color: #1d4fd2;
  font-size: 30px;
}

.titi {
  color: #a0cfff;
  font-size:20px ;
  font-weight: 400;
}
.tit {
  color: #1d4fd2;
  font-size: 25px;
  font-weight: 700;
}

.con-box button:hover {
  //background-color: #d3b7d8;
  color: #fff;
  transition: all .5s;
  background-color: #4877ee;
}

  .background {
    background-image: url('./2.jpg');
    background-size: cover;
    background-position: center;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -1; /* 确保背景图像在内容之后 */
  }
</style>
