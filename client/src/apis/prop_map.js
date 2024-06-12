import request from "@/utils/request";
import createStore from "@/store/index";

const jwt = `Bearer ${createStore.state.accessJwt}`;

export const UploadFile = (params) => {
    return request({
        url: "/prop_upload/",
        method: "post",
        data: params,
        headers: {
            "Content-Type": "multipart/form-data",
            Authorization: jwt,
        },
    });
};
