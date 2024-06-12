<template>
  <div>
    <div>
      <el-form-item
          label="上传代码"
          v-loading="uploadLoading"
          element-loading-text="上传中..."
      >
        <el-upload
            style="width: 100%"
            drag
            action=""
            :accept="acceptTypes"
            :show-file-list="false"
            :http-request="uploadToServer"
            multiple
        >
          <el-icon class="el-icon--upload">
            <upload-filled/>
          </el-icon>
          <div class="el-upload__text">
            把需要上传的文件拖拽到这里<em>点我上传</em>
          </div>
        </el-upload>
      </el-form-item>
    </div>
    <el-divider/>
    <div class="flex flex-nowrap justify-around items-center h-[500px] border rounded">
      <div style=" width: 100%;  height: 100%; overflow: scroll; overflow-x: hidden;">
        <span v-if="showRadioGroup" style="display: flex; justify-content: center; font-size: 20px; margin-top: 10px">(点击下列故障传播函数以查看故障传播路径)</span>
        <el-radio-group v-model="selectOp" class="ml-4" style="margin-left: 15%">
          <el-radio v-for="item in result.nodes" :value="item.id" style="flex-basis: 40%; max-width: 40%; margin-bottom: 10px" @click="handleRadioClick(item.id)">
            <span style="font-size: 20px;">{{ item.label }}</span>
          </el-radio>
        </el-radio-group>
          <div class="compass-icon" v-if="!showRadioGroup">
            <el-icon><Compass /></el-icon>
            <span style="display: block; font-size: 14px;  margin-top: -15px; margin-left:-35px">上传后函数名将在此显示</span>
          </div>
      </div>
      <div class="w-full h-full border-l">
        <div
            style="
                        height: 90%;
                        width: 100%;
                        background-color: rgba(255, 255, 255, 0.3);
                    "
            ref="echartsRef"
        ></div>
           <div class="histogram-icon" v-if="!showRadioGroup">
             <el-icon><MagicStick /></el-icon>
             <span style="display: block; font-size: 14px; margin-top: -17px; margin-left:-27px;">故障传播图将在此显示</span>
           </div>
           <div v-if= "showCircles" class="circle-container">
             <div class="circle" style="background-color: red;"></div>
             <span class="circle-text" >故障表象函数</span>
             <div class="circle" style="background-color: yellow;"></div>
             <span class="circle-text">故障源函数</span>
             <div class="circle" style="background-color: #a0cfff;"></div>
             <span class="circle-text">未受影响</span>
           </div>
      </div>
    </div>
    <el-dialog :visible="loading" :show-close="false" :close-on-click-modal="false" :close-on-press-escape="false" :lock-scroll="false">
      <span>Loading...</span>
    </el-dialog>
  </div>
</template>

<script setup>
import * as echarts from "echarts";
import {ref, onMounted, reactive, watch} from "vue";
import {UploadFile} from "@/apis/prop_map";

//control the coloredcircle
const loading = ref(false); // 添加加载状态变量
const showCircles = ref(false);
const showRadioGroup = ref(false);
const uploadLoading = ref(false);
const acceptTypes = ref(".py");
const echartsRef = ref(null);
const selectOp = ref(null);
const handleRadioClick = (selectedId) => {
  // 在这里设置 showCircles 为 true，例如：
  showCircles.value = true;
};
const result = reactive({
  nodes: [],
  edges: [],
});
const echatData = reactive({
  nodes: [],
  edges: [],
  links: [],
});

const uploadToServer = (file) => {
  uploadLoading.value = true; // 设置上传状态为true

  const formData = new FormData();
  formData.append("file", file.file);
  UploadFile(formData).then((res) => {
    const {status_code, msg, echats, result_set} = res;
    console.log(result_set);
    if (status_code !== 20000) {
      ElMessage({
        message: msg,
        type: "error",
        duration: 1500,
        onClose: () => {
          uploadLoading.value = false;
        },
      });

      return;
    } else {
      loading.value = true; // 显示加载模态框
      const echartsData = JSON.parse(echats);
      result.nodes.length = 0;
      result.edges.length = 0;
      result.nodes = echartsData.nodes;
      result.edges = echartsData.edges;
      ElMessage({
        message: msg,
        type: "success",
        duration: 1500,
        onClose: () => {
          uploadLoading.value = false;
        },
      });
      initChart();
      showRadioGroup.value = true;
    }
  });
};


watch(selectOp, (newVal, oldVal) => {
  const chart = echarts.init(echartsRef.value);
  const highlightedNodeId = newVal;
  const connectedNodeIds = echatData.edges
      .filter(
          (edge) =>
              edge.source === highlightedNodeId ||
              edge.target === highlightedNodeId
      )
      .map((edge) =>
          edge.source === highlightedNodeId ? edge.target : edge.source
      );


  const option = {
    series: [
      {
        emphasis: {
          focus: "adjacency",
        },

        data: echatData.nodes.map((node) => ({
          ...node,
          itemStyle: {
            color: node.name === highlightedNodeId ? "red" : connectedNodeIds.includes(node.name) ? "yellow" : "#a0cfff",
          },

          name: node.label,
          label: node.label,
          id: node.label,
        })),


        links: echatData.edges.map((edge) => ({
          ...edge,
          lineStyle: {
            color:
                edge.source === highlightedNodeId ||
                edge.target === highlightedNodeId
                    ? "red"
                    : "blue", // 根据是否与highlightedNodeId相连设置颜色
          },
        })),
      },
    ],
  };
  chart.setOption(option);
});

const initChart = () => {
  const chart = echarts.init(echartsRef.value);
  echatData.nodes.length = 0;
  echatData.edges.length = 0;
  echatData.links.length = 0;
  result.nodes.forEach((node) => {
    echatData.nodes.push({
      name: node.label,
      label: node.label,
    });
  });

  result.edges.forEach((edge) => {
    echatData.edges.push({
      source: edge.from,
      target: edge.to,
    });
  });

  console.log(echatData);

  // 指定图表的配置项和数据
  const option = {

    tooltip: {},
    series: [
      {
        type: "graph",
        layout: "force",
        symbolSize: 20,
        roam: true,
        label: {
          show: true,
        },
        force: {
          repulsion: 300,
        },
        data: echatData.nodes,
        links: echatData.edges,
      },
    ],
  };
  chart.setOption(option);
};

onMounted(() => {
  initChart();
});
</script>

<!--<style>-->
<!--.item{-->
<!--  color: #a0cfff;-->
<!--}-->
<!--</style>-->
<style>
.circle-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.circle {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  margin-right: 5px;
}

.circle-text {
  margin-top:-2px;
  margin-right:10px;
  font-size: 14px; /* 调整字体大小 */
  font-weight: bold; /* 加粗 */
}

.compass-icon {
    position: relative;
    top: 30%;
    left: 42%;
    font-size: 70px;
    color: #999;
  }

.histogram-icon {
    position: relative;
    bottom: 55%;
    left: 42%;
    font-size: 70px;
    color: #999;
  }
</style>