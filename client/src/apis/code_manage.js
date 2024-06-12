import request from "@/utils/request";
import createStore from "@/store/index";

const jwt = `Bearer ${createStore.state.accessJwt}`;

export const getData = (params) => {
    return request({
        url: "/code_manage/",
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
        url: "/code_manage/",
        method: "delete",
        data: params,
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
    });
};

export const showCode = (params) => {
    return request({
        url: "/code_manage/",
        method: "post",
        data: params,
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
    });
};
