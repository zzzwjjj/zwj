<template>
  <div>
    <div class="form">
      <el-form :inline="true" :model="formInline" class="demo-form-inline">
        <el-form-item label="文件名称">
          <el-input v-model="formInline.fileName" clearable placeholder="文件名称"></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSubmit">查询</el-button>
        </el-form-item>
      </el-form>
    </div>
    <div class="common-layout">
      <div class="scrollable-container">
        <div class="content">
          <div class="item" v-for="(item,index) in FileList.slice((currentPage-1)*pageSize,currentPage*pageSize)" :key="index" @click="showCallGraph(item)">
           <img src="../../assets/python.png " alt="">
           <div class="text">{{ item.file }}</div>
          </div>
        </div>
      </div>
    </div>
    <div class="">
      <el-pagination 
      align='center' 
      @size-change="handleSizeChange" 
      @current-change="handleCurrentChange" 
      :current-page="currentPage" :page-sizes="[8,12,16]" 
      :page-size="pageSize" 
      layout="total, sizes, prev, pager, next, jumper" 
      :total="FileList.length">
			</el-pagination>
    </div>
    <el-dialog width="40%" title="函数调用图"  v-model="dialogTableVisible">
      <div class="content_dialog" id="echarts">

      </div>
    </el-dialog>
  </div>
</template>

<script>
import axios from 'axios';
import * as echarts from 'echarts';
import createStore from "@/store/index.js";
import {getListCall,getListCallDetail} from "@/apis/faultProp.js"
export default {
  data() {
    return {
      dialogTableVisible: false,
      formInline: {
          fileName: '',
        },
        FileList:[],
        echatData:{
          nodes:[],
          edges:[],
        },
        currentPage: 1, // 当前页码
			  total: 12, // 总条数
			  pageSize: 12 // 每页的数据条数
    };
  },
  methods: {
    handleSizeChange(val) {
			this.currentPage = 1;
			this.pageSize = val;
		},
		handleCurrentChange(val) {
			this.currentPage = val;
		},
    onSubmit(){
      this.fetchRespDict()
    },
    async fetchRespDict() {
      let query = {
        file: this.formInline.fileName
      }
      try {
        getListCall(query).then((res) => {
          this.FileList = res.data
        })
      } catch (error) {
        console.error('获取文件列表失败：', error);
      }
    },
    async showCallGraph(data) {
      this.dialogTableVisible = true
     await getListCallDetail({file:data.file}).then((res) => {
        console.log(res,"getListCallDetail")
        let result = res.data
        let  categories = [
            {
              "name": "A"
            },
            {
              "name": "B"
            },
            {
              "name": "C"
            },
            {
              "name": "D"
            },
            {
              "name": "E"
            },
            {
              "name": "F"
            },
            {
              "name": "G"
            },
            {
              "name": "H"
            },
            {
              "name": "I"
            }
          ]
        this.echatData.edges = []
        this.echatData.nodes = []
        result.nodes.forEach((node) => {
          this.echatData.nodes.push({
            name: node.label,
            symbolSize: 10,
            label: node.label,
            category: parseInt(Math.random()*10)
          });
        });

        result.edges.forEach((edge) => {
          this.echatData.edges.push({
            source: edge.from,
            target: edge.to,
          });
        });
        var chartDom = document.getElementById('echarts');
        var myChart = echarts.init(chartDom);
          const option = {

            tooltip: {},
            legend: [
              // {
              //   // selectedMode: 'single',
              //   data: categories.map(function (a) {
              //     return a.name;
              //   })
              // }
            ],
            series: [
              {
                type: "函数调用图",
                type: 'graph',
                layout: "force",
                symbolSize: 20,
                roam: true,
                label: {
                  show: true,
                },
                categories: categories,
                force: {
                  repulsion: 300,
                },
                data: this.echatData.nodes,
                links: this.echatData.edges,
              },
            ],
          };
          myChart.setOption(option);
      })
      // this.selectedFileName = fileName;
      // this.callGraphDialog.visible = true;
      // // 绘制调用图的逻辑
      // this.drawCallGraph(graphData);
    },
    drawCallGraph(data) {
      const chartDom = document.getElementById('callGraphChart');
      const myChart = echarts.init(chartDom);
      // 绘制图表
      myChart.setOption(data);
    },
    closeCallGraphDialog() {
      this.callGraphDialog.visible = false;
    }
  },
  mounted() {
    this.fetchRespDict();
  }
};
</script>
<style scoped lang="scss">

.scrollable-container {
    height: calc(700px - 50px); /* 固定容器高度，减去头部的高度 */
    overflow: scroll; /* 添加垂直滚动条 */
  overflow-x: hidden; /* 禁用水平滚动条 */
}
.content{
  width: 100%;
  height: auto;
  display: flex;
  flex-wrap: wrap;
  padding-left:30px;

  .item{
    width: 300px;
    //宽度
    height:auto;
    margin-left:30px;
    margin-top:30px;


   // margin: 0 0 30px 20px;
    //? ? ? 右间隔
    border: 1px solid #999;
    border-radius: 10px;
    padding-top: 10px;
    padding-bottom: 10px;
    //margin-right: 20px;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 5px rgba(0, 0, 0, 0.2); /* 添加普通的阴影效果 */
    img{
      width: auto;
      height: 110px;
      border-radius: 10px;
      object-fit: contain; /* 让图片保持原始比例并居中 */
    }

    .text{
      font-size: 14px;
      font-weight: 600;
      color: #000;
      text-align: center;
      line-height: 20px;
      height: 20px;
      margin-top: 20px;
    }
  }

  .item:hover {
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.5); /* 添加阴影效果，使容器突出 */
  transform: scale(1.05); /* 悬停时容器放大 5% */
  }

}
.content_dialog{
  width: 600px;
  height: 500px;
}
</style>