import { createStore } from "vuex";
import createPersistedState from "vuex-persistedstate";

export default createStore({
    state: {
        refreshJwt: null,
        accessJwt: null,
        userName: null,
        modifyNavigation: null,
    },
    mutations: {
        // 修改state参数等方法
        paramsReset(state, params) {
            // 需要在params中传递一个{key:xx,value:xx},用key查询store字段，在用 value进行修改
            // 先检查key是否存在

            if (
                params.hasOwnProperty("key") &&
                params.hasOwnProperty("value")
            ) {
                const key = params["key"];
                const value = params["value"];
                state[key] = value;
            } else {
                // 传递的修改参数不符合
                return Promise.reject(
                    new Error("字段不符合要求，必须要包含key、value")
                );
            }
        },
    },
    plugins: [
        createPersistedState({
            key: "code_detection",
            storage: window.sessionStorage,
        }),
    ],
});
