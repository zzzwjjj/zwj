import request from "@/utils/request";
import createStore from "@/store/index";

const jwt = `Bearer ${createStore.state.accessJwt}`;

export const deleteCode = (params) => {
    return request({
        url: "/delete/",
        method: "post",
        data: params,
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            Authorization: jwt,
        },
    });
};