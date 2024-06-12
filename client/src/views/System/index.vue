<template>
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
                v-model="searchOpName"
                placeholder="请输入操作类型"
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

    <el-table :data="tableData" style="width: 100%">
        <el-table-column type="index" label="编号" align="center" width="80" />
        <el-table-column prop="op_name" label="操作类型" align="center" />
        <el-table-column prop="created" label="操作时间" align="center" width="180">
        </el-table-column>
    </el-table>

    <el-divider />
    <div class="example-pagination-block">
        <el-pagination
            background
            @change="pageHandle"
            layout="prev, pager, next"
            :total="totalCount"
        />
    </div>
</template>

<script setup>
import { ref, reactive, onMounted , nextTick} from "vue";
import * as vis from "vis";
import {getData} from "@/apis/system";
const searchDate = ref(null);
const searchOpName = ref(null);
const tableData = reactive([]);
const nowPage = ref(1);
const totalCount = ref(1);
const dialogShow = ref(false);
const startDate = ref(null);
const endDate = ref(null);


const disabledDateFn = (time) => {
  return time.getTime() > Date.now();
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
    op_name: searchOpName.value,
  });
};

const getTableData = async (params) => {
  getData(params).then((res) => {
    const {status_code, msg, all_count, now_page, data} = res;
    totalCount.value = all_count;
    nowPage.value = now_page;
    tableData.length = 0;
    for (let i in data) {
      // if(data[i].ext.file_name){
        tableData.push(data[i]);
      // }
    }
    console.log(data);
  });
};

const pageHandle = async (val) => {
  nowPage.value = val;
  await getTableData({
    page: nowPage.value,
    start_date: startDate.value,
    end_date: endDate.value,
    op_name: searchOpName.value,
  });
};
onMounted(async () => {
  await getTableData({page: nowPage.value});
});
// onMounted(async () => {
//     await getUserOpLog();
// });
</script>
