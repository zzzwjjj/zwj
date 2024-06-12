<template>
<!--  <el-row>-->
<!--    <el-col :span="15">-->
<!--      <div class="">-->
        <el-row :gutter="24">
          <el-col :span="6">
            <el-date-picker
                :disabled-date="disabledDateFn"
                v-model="searchDate"
                type="daterange"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                start-placeholder="开始日"
                end-placeholder="截止日"
                range-separator="~"
                size="default"
            />
          </el-col>
          <el-col :span="6">
            <el-input
                v-model="searchFileName"
                placeholder="请输入文件名称"
                type="text"
                size="default"
            />
          </el-col>
          <el-col :span="6">
            <el-button
                @click="SearchBtnClient"
                type="primary"
                icon="Search"
                circle
            />
          </el-col>
        </el-row>
<!--      </div>-->
<!--    </el-col>-->
<!--  </el-row>-->
  <el-divider/>
  <el-button v-show="deleteBtnShow" @click="deleteSelectionBtn" type="danger"
  >批量删除
  </el-button
  >
  <el-divider/>
  <el-table
      :data="tableData"
      @selection-change="handleSelectionChange"
      style="width: 100%"
  >
    <el-table-column type="selection" width="30" align="center"/>
    <el-table-column prop="sid" label="编号" width="80" align="center"/>
    <el-table-column prop="ext.file_name" label="文件名" align="center"/>
    <el-table-column prop="ext.username" label="上传用户" align="center"/>
    <el-table-column prop="created" label="创建时间" width="180" align="center">
    </el-table-column>
    <el-table-column align="center" label="操作">
      <template #default="scope">
        <el-button
            type="primary"
            @click="showCodeInfo(scope)"
            icon="Notebook"
        >查看代码
        </el-button
        >
        <el-button
            type="danger"
            @click="deleteOneScope(scope)"
            icon="Delete"
        >删除代码
        </el-button
        >
        <!-- <el-button @click="createChats(scope)" type="primary"
            >生成拓扑图</el-button
        > -->
      </template>
    </el-table-column>
  </el-table>
  <el-divider/>
  <div class="example-pagination-block">
    <el-pagination
        background
        @change="pageHandle"
        layout="prev, pager, next"
        :total="totalCount"
    />
  </div>

  <el-dialog v-model="dialogShow" style="height: 650px" title="网络拓扑图">
    <template #default>
      <div ref="visualizationRef" element-loading-text="生成中..."></div>
    </template>
  </el-dialog>

  <el-dialog v-model="dialogCodeShow" class="h-auto" title="代码详情图">
    <template #default>
      <div class="border rounded h-full" style="overflow: scroll">
        <pre class="h-full" v-html="highlightedCode"></pre>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import {ref, reactive, onMounted, nextTick} from "vue";
import * as vis from "vis";
import {getData, deleteSidList, showCode} from "@/apis/code_manage";
import hljs from "highlight.js";
import "highlight.js/styles/default.css"; // 选择你喜欢的样式主题
import {deleteCode} from "@/apis/delete";
// 引入Python语言的高亮定义
import python from "highlight.js/lib/languages/python";

hljs.registerLanguage("python", python);

const searchDate = ref(null);
const searchFileName = ref(null);
const visualizationRef = ref(null);

const tableData = reactive([]);
const nowPage = ref(1);
const totalCount = ref(1);
const dialogShow = ref(false);
const startDate = ref(null);
const endDate = ref(null);
const multipleSelection = ref([]);
const deleteBtnShow = ref(false);
const deleteItemList = reactive([]);
const deleteItemList_file = reactive([]);
const dialogCodeShow = ref(false);

const pythonCode = ref(`
from django.urls import path
from api.views.account_views import RegisterView,UserInfoView
from api.views.uploadfiles_views import UploadFilesView
from api.views.fault_location_views import FaultLocationView
from api.views.code_manage_views import CodeManageView
from api.views.system_views import GetUserLogView
from api.views.total_views import TotalView
def hello_world():
    print("Hello, World!")
    `);

const highlightedCode = ref("");



const showCodeInfo = async (scope) => {
  dialogCodeShow.value = false;
  console.log('1111');
  console.log(scope.row.ext.file_name);
  showCode({sid: scope.row.sid}).then((res) => {
    const {status_code, msg, data} = res;
    if (status_code != 20000) {
      ElMessage({
        message: msg,
        type: "error",
        duration: 1500,
      });
      return;
    } else {
      pythonCode.value = data;
      highlightedCode.value = hljs.highlight(pythonCode.value, {
        language: "python",
      }).value;
      dialogCodeShow.value = true;
    }
  });
};

const deleteSelectionBtn = async () => {
  deleteItemList.length = 0;
  for (let item in multipleSelection.value) {
    deleteItemList.push(multipleSelection.value[item].sid);
  }
  deleteItemList_file.length = 0;
  for (let item in multipleSelection.value) {
    deleteItemList_file.push(multipleSelection.value[item].ext.file_name);
  }
  deleteCode({
      file_name:deleteItemList_file
  })
  ElMessageBox.confirm('此操作将永久删除该数据, 是否继续?', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
  deleteSidList(JSON.stringify({sid_list: deleteItemList})).then((res) => {
    const {status_code} = res;
    if (status_code == 20000) {
      ElMessage({
        message: `删除成功`,
        type: "success",
        duration: 1500,
        onClose: () => {
          getTableData({page: nowPage.value});
        },
      });
    }
  });
  }).catch(() => {
          ElMessage({
            type: 'info',
            message: '已取消删除'
          });
        });
};


const deleteOneScope = async (scope) => {
  deleteItemList.length = 0;
  deleteItemList.push(scope.row.sid);
  deleteItemList_file.length = 0;
  deleteItemList_file.push(scope.row.ext.file_name);
  deleteCode({
      file_name:deleteItemList_file
    })
      ElMessageBox.confirm('此操作将永久删除该数据, 是否继续?', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
  deleteSidList(JSON.stringify({sid_list: deleteItemList})).then((res) => {

    const {status_code} = res;
    if (status_code == 20000) {
      ElMessage({
        message: `删除成功`,
        type: "success",
        duration: 1500,
        onClose: () => {
          getTableData({page: nowPage.value});
        },
      });
    }
  });
  }).catch(() => {
          ElMessage({
            type: 'info',
            message: '已取消删除'
          });
        });
};

const handleSelectionChange = (val) => {
  multipleSelection.value = val;
  if (multipleSelection.value.length > 0) {
    deleteBtnShow.value = true;
  } else {
    deleteBtnShow.value = false;
  }
};

const SearchBtnClient = async () => {
  if (searchDate.value) {
    startDate.value = searchDate.value[0];
    endDate.value = searchDate.value[1];
  }

  await getTableData({
    page: 1,
    start_date: startDate.value,
    end_date: endDate.value,
    file_name: searchFileName.value,
  });
};

const showChats = async (scope) => {
  nextTick(() => {
    const jsonData = JSON.parse(scope.row.ext);
    const container = visualizationRef.value;
    const nodes = new vis.DataSet(jsonData.nodes);
    const edges = new vis.DataSet(jsonData.edges);
    let data = {
      nodes: nodes,
      edges: edges,
    };
    let options = {
      nodes: {},
      interaction: {
        hover: true,
        hoverConnectedEdges: true,
      },
      layout: {},
    };
    const network = new vis.Network(container, data, options);
  });
};

const createChats = async (scope) => {
  dialogShow.value = true;
  showChats(scope);
};

const getTableData = async (params) => {
  getData(params).then((res) => {
    const {status_code, msg, all_count, now_page, data} = res;
    totalCount.value = all_count;
    nowPage.value = now_page;
    tableData.length = 0;
    for (let i in data) {
      if(data[i].ext.file_name){
        tableData.push(data[i]);
      }

    }
    console.log(data);
  });
};

const disabledDateFn = (time) => {
  return time.getTime() > Date.now();
};

const pageHandle = async (val) => {
  nowPage.value = val;
  await getTableData({
    page: nowPage.value,
    start_date: startDate.value,
    end_date: endDate.value,
    file_name: searchFileName.value,
  });
};

onMounted(async () => {
  await getTableData({page: nowPage.value});
});
</script>

<style lang="scss" scoped>
@import "highlight.js/styles/github.css";

.el-dialog__body,
.el-dialog__body div {
  height: 450px;
}
</style>
