import request from "@/utils/request";
import createStore from "@/store/index";

const jwt = `Bearer ${createStore.state.accessJwt}`;

export const getData = (params) => {
    return request({
        url: "/user/",
        method: "get",
        params: params,
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
    });
};

export const deleteSidList = (params) => {
    return request({
        url: "/user/delete/",
        method: "put",
        data: params,
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
    });
};

export const setUpdate = (id,params) => {
    return request({
        url: `/user_upgrade/${id}/upgrade/`,
        method: "put",
        data: params,
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
    });
};
export const setUserUpdate = (id,params) => {
    return request({
        url: `/user/${id}/`,
        method: "put",
        data: params,
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
    });
};


export const setpassword = (id,params) => {
    return request({
        url: `/set_password/${id}/upgrade/`,
        method: "put",
        data: params,
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
    });
};