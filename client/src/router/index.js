import { createRouter, createWebHistory } from "vue-router";
import store from "@/store";

const router = createRouter({
    history: createWebHistory(import.meta.env.VITE_BASE_PATH),
    routes: [
        {
            path: "/",
            name: "LoginPage",
            meta: { title: "首页" },
            component: () => import("@/pages/loginPage/index.vue"),
        },
        {
            path: "/index",
            name: "IndexPage",
            meta: { title: "后台管理" },
            component: () => import("@/pages/frame/index.vue"),
            redirect: "/welcome",
            children: [
                {
                    path: "/welcome",
                    name: "Welcomepage",
                    meta: { title: "欢迎页" },
                    component: () => import("@/views/WelcomePage/index.vue"),
                },
                {
                    path: "/fault_location",
                    name: "FaultLoacation",
                    meta: { title: "故障预测" },
                    component: () => import("@/views/FaultLocation/index.vue"),
                },
                {
                    path: "/fault_prop",
                    name: "FaultProp",
                    meta: { title: "故障传播图" },
                    component: () => import("@/views/FaultProp/index.vue"),
                },
                {
                    path: "/Function_calls",
                    name: "FunctionCall",
                    meta: { title: "函数调用图" },
                    component: () => import("@/views/FunctionCall/index.vue"),
                },
                {
                    path: "/prop_map",
                    name: "PropMap",
                    meta: { title: "故障定位" },
                    component: () => import("@/views/PropMap/index.vue"),
                },
                {
                    path: "/analysis",
                    name: "Analysis",
                    meta: { title: "查询统计" },
                    component: () => import("@/views/Analysis/index.vue"),
                },
                {
                    path: "/code_manage",
                    name: "CodeManage",
                    meta: { title: "代码管理" },
                    component: () => import("@/views/CodeManage/index.vue"),
                },
                {
                    path: "/system",
                    name: "System",
                    meta: { title: "操作日志" },
                    component: () => import("@/views/System/index.vue"),
                },
                {
                    path: "/user",
                    name: "User",
                    meta: { title: "用户管理" },
                    component: () => import("@/views/User/index.vue"),
                },
                // {
                //     path: "/fileManage",
                //     name: "FileManage",
                //     meta: { title: "文件管理" },
                //     component: () => import("@/views/FileManage/index.vue"),
                // },
                {
                    path: "/history",
                    name: "History",
                    meta: { title: "查询统计" },
                    component: () => import("@/views/History/index.vue"),
                },
            ],
        },
    ],
});

// 增加页面title，修改页面的title
router.beforeEach((to, form, next) => {
    if (to.meta.title) {
        document.title = `${to.meta.title} - 故障分析平台`;
        // 修改进入后的导航条样式
        store.commit("paramsReset", {
            key: "modifyNavigation",
            value: to.meta.title,
        });
    }
    next();
});

export default router;
