import { createApp } from "vue";

import App from "./App.vue";
import "normalize.css";
import router from "@/router";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";

import ElementPlus from "element-plus";
import zhCn from "element-plus/dist/locale/zh-cn.mjs";
import "@/styles/index.scss";

const app = createApp(App);

app.use(router).mount("#app");

for (let i in ElementPlusIconsVue) {
    app.component(i, ElementPlusIconsVue[i]);
}

app.use(ElementPlus, {
    locale: zhCn,
});
