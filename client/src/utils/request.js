import axios from "axios";

const service = axios.create({
    // 根据项目的状态，自动切换请求的服务地址
    baseURL: "/api",
    timeout: 20000,
});

/*
响应拦截器
服务端返回数据之后，前端.then之前被调用
*/
service.interceptors.response.use((response) => {
    const { statusText, status, data } = response;
    if (status == 200) {
        return data;
    }

    // Todo:业务请求错误
    return Promise.reject(new Error(response));
});

export default service;
