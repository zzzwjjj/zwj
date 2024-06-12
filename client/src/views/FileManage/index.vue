<template>
    <div>
          <el-row :gutter="20">
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
                      clearable
                      placeholder="请输入文件名"
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
          <el-divider/>
          <el-button v-show="deleteBtnShow" @click="deleteSelectionBtn" type="danger">批量删除</el-button>
          <el-divider/>
          <div class="table-container" ref="tableContainer">
              <el-table
                  :data="tableData"
                  @selection-change="handleSelectionChange"
                  style="width: 100%"
              >
                <el-table-column type="selection" width="30" align="center"/>
                <el-table-column prop="index" label="序号" width="80" align="center"/>
                <el-table-column prop="file_name" label="文件名" align="center" width="300" >

                </el-table-column>
                <el-table-column prop="upload_user" label="上传人" width="300" align="center"/>
                <el-table-column prop="create_time" label="加入时间" width="200" align="center">

                </el-table-column>
                <el-table-column align="center" label="操作">
                  <template #default="{row}">
                    <el-button
                        type="danger"
                        @click="deleteOneScope(row)"
                        icon="Delete"
                    >删除
                    </el-button
                    >
                  </template>
                </el-table-column>
              </el-table>
          </div>
          <el-divider/>
          <div class="example-pagination-block">
              <el-pagination
                  @size-change="handleSizeChange"
                  @current-change="handleCurrentChange"
                  :current-page="page"
                  :page-sizes="[10, 20, 30, 40]"
                  :page-size="pageSize"
                  layout="total, sizes, prev, pager, next, jumper"
                  :total="totalCount">
                  </el-pagination>
          </div>
  </div>
</template>
  
  <script setup>
  import {ref, reactive, onMounted, nextTick} from "vue";
  import {getData, deleteSidList} from "@/apis/file_manage";
  const searchFileName = ref(null);
  const searchDate = ref(null);
  const startDate = ref(null);
  const endDate = ref(null);

  const visualizationRef = ref(null);
  
  const tableData = reactive([]);
  const page = ref(1);
  const pageSize = ref(10);
  const totalCount = ref(1);
  const multipleSelection = ref([]);
  const deleteBtnShow = ref(false);
  const deleteItemList = reactive([]);
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


  const deleteSelectionBtn = async () => {
    deleteItemList.length = 0;
    for (let item in multipleSelection.value) {
      deleteItemList.push(multipleSelection.value[item].id);
    }
    ElMessageBox.confirm('此操作将永久删除该数据, 是否继续?', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
          deleteSidList(JSON.stringify({ids: deleteItemList})).then((res) => {
            const {status_code} = res;
            if (status_code == 20000) {
              ElMessage({
                message: `删除成功`,
                type: "success",
                duration: 1500,
                onClose: () => {
                  getTableData();
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
  const deleteOneScope = async (row) => {
    deleteItemList.length = 0;
    deleteItemList.push(row.id);
    ElMessageBox.confirm('此操作将永久删除该数据, 是否继续?', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
          deleteSidList(JSON.stringify({ids: deleteItemList})).then((res) => {
            const {status_code} = res;
            if (status_code == 20000) {
              ElMessage({
                message: `删除成功`,
                type: "success",
                duration: 1500,
                onClose: () => {
                  getTableData();
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
    await getTableData();
  };
  
  const getTableData = async () => {
    let params ={
        start_date: startDate.value,
        end_date: endDate.value,
        file: searchFileName.value,
        page:page.value,
        pageSize:pageSize.value
    }
    getData(params).then((res) => {
        console.log(res,"res")
      const {status_code, msg, count, results} = res.data;
      totalCount.value = count;
      tableData.length = 0;
      results.forEach((item,index) => {
        let obj = {
            index: index + 1,
            ...item
        }
        tableData.push(obj);
      })
    });
  };
  
  const disabledDateFn = (time) => {
    return time.getTime() > Date.now();
  };
  
  const handleSizeChange = async (val) => {
    pageSize.value = val;
    await getTableData();
  };
  const handleCurrentChange = async (val) => {
    page.value = val;
    await getTableData();
  };
  
  onMounted(async () => {
    await getTableData();
  });
  </script>
  
  <style lang="scss">
  @import "highlight.js/styles/github.css";
  .table-container {
  width: 100%;
  height: 500px; /* 设定容器的高度，超出高度的内容将会垂直滚动 */
  overflow-y: auto; /* 垂直滚动 */
   overflow-x: hidden; /* 禁用水平滚动条 */
}

  </style>