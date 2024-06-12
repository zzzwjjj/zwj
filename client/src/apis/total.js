import request from "@/utils/request";
import createStore from "@/store/index";

const jwt = `Bearer ${createStore.state.accessJwt}`;

export const getChatsData = (params) => {
    return request({
        url: "/total/",
        method: "get",
        params: params,
        headers: {
            "Content-Type": "multipart/form-data",
            Authorization: jwt,
        },
    });
};
