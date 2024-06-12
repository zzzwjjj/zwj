import request from "@/utils/request";
import createStore from "@/store/index";

const jwt = `Bearer ${createStore.state.accessJwt}`;
export const getList = (params) => {
    return request({
        url: `/fault_prop/?file=${ params.file}`,
        method: "get",
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
       
    });
};
export const getListDetail = (data) => {
    return request({
        url: "/fault_prop/",
        method: "post",
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
        data
    });
};
export const getListCall = (params) => {
    return request({
        url: `/func_call/?file=${ params.file}`,
        method: "get",
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        }
    });
};
export const getListCallDetail = (data) => {
    return request({
        url: "/func_call/",
        method: "post",
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
        data
    });
};