<script setup></script>

<template>
    <router-view />
</template>

<style lang="scss" scoped>
body {
    /* 100%窗口高度 */
    min-height: 100vh;
    width: 100vw;
    /* 弹性布局 水平+垂直居中 */
    display: flex;
    justify-content: center;
    align-items: center;
    /* 渐变背景 */
    background: #f2f4f7;
    #app {
        width: 100%;
        height: 100%;
        padding: 0;
        margin: 0;

    }
}
</style>
