<template>
  <el-row :gutter="10" class="mt-2">
    <el-col :span="12">
      <el-card class="" style="height: 450px; width: 100%">
        <div
            v-loading="echartsPieLoading"
            element-loading-text="数据加载ing..."
            style="
                        height: 100%;
                        width: 100%;
                        background-color: rgba(255, 255, 255, 0.3);
                    "
            ref="echartsPieRef"
        ></div>
      </el-card
      >
    </el-col>
    <el-col :span="12"
    >
      <el-card class="" style="height: 450px; width: 100%">
        <div
            v-loading="echartsZhuLoading"
            element-loading-text="数据加载ing..."
            style="
                        height: 100%;
                        width: 100%;
                        background-color: rgba(255, 255, 255, 0.3);
                    "
            ref="echartsZhuRef"
        ></div>
      </el-card
      >
    </el-col>
  </el-row>


  <el-row :gutter="10" class="mt-2">
    <el-col :span="12">
      <el-card class="" style="height: 450px; width: 100%">
      <el-select v-model="selectedDays" placeholder=最近一周 style="background-color: white; color: white; max-width: 150px;">
        <el-option label=最近一周 value="最近一周" @click="drawLineBefareChart(7)"></el-option>
        <el-option label=最近半个月 value="最近半个月" @click="drawLineBefareChart(15)"></el-option>
        <el-option label=最近一个月 value="最近一个月" @click="drawLineBefareChart(30)"></el-option>
      </el-select>
        <div
            v-loading="echartsLineBeforeLoading"
            element-loading-text="数据加载ing..."
            style="
                        height: 100%;
                        width: 100%;
                        background-color: rgba(255, 255, 255, 0.3);
                    "
            ref="echartsLineBeforeRef"
        ></div>
      </el-card
      >
    </el-col>
    <el-col :span="12"
    >
      <el-card class="" style="height: 450px; width: 100%">
        <el-select  v-model="selectedDay"  placeholder=最近一周 style="background-color:white; color: white;max-width: 150px;">
          <el-option label=最近一周  value="最近一周"  @click="drawLineAfterChart(7)"></el-option>
          <el-option label=最近半个月 value="最近半个月" @click="drawLineAfterChart(15)"></el-option>
          <el-option label=最近一个月 value="最近一个月" @click="drawLineAfterChart(30)"></el-option>
        </el-select>

        <div
            v-loading="echartsLineAfterLoading"
            element-loading-text="数据加载ing..."
            style="
                        height: 100%;
                        width: 100%;
                        background-color: rgba(255, 255, 255, 0.3);
                    "
            ref="echartsLineAfterRef"
        ></div>
      </el-card>
    </el-col>
  </el-row>

  <!--    </div>-->
  <!--  </div>-->
</template>

<script setup>
import {ref, reactive, onMounted} from "vue";
import * as echarts from "echarts";
import {getChatsData} from "@/apis/total";

const echartsPieRef = ref(null);
const echartsPieLoading = ref(true);
const echartsZhuRef = ref(null);
const echartsZhuLoading = ref(true);
const echartsLineBeforeLoading = ref(true);
const echartsLineAfterLoading = ref(true);
const echartsLineBeforeRef = ref(null);
const echartsLineAfterRef = ref(null);


const drawLineAfterChart = async (day) => {
  echartsLineAfterLoading.value = true;
  const chart = echarts.init(echartsLineAfterRef.value);
  // 获取数据
  let res = await getChatsDataFunc({echats_name: "line_after", days: day});
  console.log(res);
  const option = {
    tooltip: {
      trigger: "axis",
    },

    legend: {
      data: ["错误", "代码质量", "封装", "环境"],
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: res.date_list,
    },
    yAxis: {
      type: "value",
    },
    series: [
      {
        name: "错误",
        type: "line",
        // stack: "Total",
        data: res.data_list["5"]["value_list"],
      },
      {
        name: "代码质量",
        type: "line",
        // stack: "Total",
        data: res.data_list["6"]["value_list"],
      },
      {
        name: "封装",
        type: "line",
        // stack: "Total",
        data: res.data_list["7"]["value_list"],
      },
      {
        name: "环境",
        type: "line",
        data: res.data_list["8"]["value_list"],
      },
    ],
  };
  chart.setOption(option);
  echartsLineAfterLoading.value = false;
};
const drawLineBefareChart = async (day) => {
  echartsLineBeforeLoading.value = true;
  const chart = echarts.init(echartsLineBeforeRef.value);
  // 获取数据
  let res = await getChatsDataFunc({echats_name: "line_before", days: day});

  const option = {

    tooltip: {
      trigger: "axis",
    },

    legend: {
      data: ["输入有效性和表示", "API滥用", "安全功能", "时间和状态"],
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: res.date_list,
    },
    yAxis: {
      type: "value",
    },
    series: [
      {
        name: "输入有效性和表示",
        type: "line",
        // stack: "Total",
        data: res.data_list["1"]["value_list"],
      },
      {
        name: "API滥用",
        type: "line",
        // stack: "Total",
        data: res.data_list["2"]["value_list"],
      },
      {
        name: "安全功能",
        type: "line",
        // stack: "Total",
        data: res.data_list["3"]["value_list"],
      },
      {
        name: "时间和状态",
        type: "line",
        // stack: "Total",
        data: res.data_list["4"]["value_list"],
      },
    ],
  };
  chart.setOption(option);
  echartsLineBeforeLoading.value = false;
};

const drawPieChart = async (day) => {
  echartsPieLoading.value = true;
  const chart = echarts.init(echartsPieRef.value);
  // 获取数据
  let res = await getChatsDataFunc({echats_name: "pie", days: day});
  const option = {
    title: {
      text: res.title_name,
      left: "center",
    },
    tooltip: {
      trigger: "item",
    },
    // legend: {
    // top: '5%',
    // left: 'left'
    // },
    series: {
      name: "错误量",
      type: "pie",
      radius: ["40%", "70%"],
      data: [],
    },
  };
  for (let item in res.data) {
    option.series.data.push(res.data[item]);
  }
    console.log(res.data);
  chart.setOption(option);
  echartsPieLoading.value = false;
};
const drawZhuChart = async (day) => {
  echartsZhuLoading.value = true;
  const chart = echarts.init(echartsZhuRef.value);

  // 获取数据
  let res = await getChatsDataFunc({echats_name: "zhu", days: day});

  const option = {
  dataset: {
    source: [
      ['score', 'amount', 'product'],
      [89.2, res.data['1'].value, '输入有效性表示'],
      [57.1, res.data['2'].value, 'API滥用'],
      [74.4, res.data['3'].value, '安全功能 '],
      [50.1, res.data['4'].value, '时间和状态'],
      [89.7, res.data['5'].value, '错误'],
      [68.1, res.data['6'].value, '代码质量'],
      [19.6, res.data['7'].value, '封装'],
      [10.6, res.data['8'].value, '环境'],
    ]
  },
  grid: { containLabel: true },
  xAxis: { name: 'amount' },
  yAxis: { type: 'category' },
  visualMap: {
    orient: 'horizontal',
    left: 'center',
    min: 10,
    max: 100,
    text: ['High Score', 'Low Score'],
    // Map the score column to color
    dimension: 0,
    inRange: {
      color: ['#65B581', '#FFCE34', '#FD665F']
    }
  },
  series: [
    {
      type: 'bar',
      encode: {
        // Map the "amount" column to X axis.
        x: 'amount',
        // Map the "product" column to Y axis
        y: 'product'
      }
    }
  ]
  };

  // for (let item in res.data) {
  //   option.series.data.push(res.data[item]);
  // }

  chart.setOption(option);
  // echartsPieLoading.value = false;
  console.log('11111');
  console.log(res.data['1'].value);
  console.log('222222');
};
const getChatsDataFunc = (params) => {
  return getChatsData(params).then((res) => {
    const {status_code, data} = res;
    if (status_code == 20000) {
      return data;
    }
    throw new Error("数据接口出错");
  });
};

onMounted(() => {
  drawPieChart(7);
  drawZhuChart(7);
  drawLineBefareChart(7);
  drawLineAfterChart(7);
});
</script>

<style lang="scss" scoped>
.el-card {
  width: 100%;
}


</style>
