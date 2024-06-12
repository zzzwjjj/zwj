import request from "@/utils/request";
import createStore from "@/store/index";

const jwt = `Bearer ${createStore.state.accessJwt}`;

export const Login = (postData) => {
    return request({
        url: "/token/",
        method: "post",
        data: JSON.parse(postData),
    });
};

export const Register = (postData) => {
    return request({
        url: "/register/",
        method: "post",
        data: JSON.parse(postData),
    });
};

export const UserInfo = () => {
    return request({
        url: "/user_info/",
        method: "post",
        headers: {                             // 解析令牌 传递数据给后端
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
    });
};
