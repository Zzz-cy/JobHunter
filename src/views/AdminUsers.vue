<template>
  <div class="admin-users-page page-container">
    <el-card class="users-card" shadow="never" v-loading="loading">
      <template #header>
        <div class="card-title">
          <span>用户账号</span>
          <div class="search-area">
            <el-input
              v-model="keyword"
              placeholder="昵称 / 手机号"
              clearable
              class="search-input"
              @keyup.enter="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
          </div>
        </div>
      </template>

      <el-table :data="items" stripe empty-text="暂无用户">
        <el-table-column prop="nickname" label="昵称" min-width="110">
          <template #default="{ row }">{{ row.nickname || '—' }}</template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" min-width="125">
          <template #default="{ row }">{{ row.phone || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.role === 'admin' ? 'warning' : 'info'" effect="plain">
              {{ row.role === 'admin' ? '管理员' : '求职者' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'banned' ? 'danger' : 'success'">
              {{ row.status === 'banned' ? '已封禁' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="145">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="最后登录" width="145">
          <template #default="{ row }">{{ formatTime(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column label="是否已建档" width="105">
          <template #default="{ row }">
            <el-tag size="small" effect="plain" :type="row.onboarded ? 'success' : 'info'">
              {{ row.onboarded ? '已建档' : '未建档' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-tag v-if="isSelf(row)" size="small" type="info">当前账号</el-tag>
            <template v-else>
              <el-button
                v-if="row.role === 'user'"
                link
                type="primary"
                size="small"
                :disabled="!!operating"
                :loading="operating === `${row.id}:role`"
                @click="handleSetRole(row, 'admin')"
              >
                设为管理员
              </el-button>
              <el-button
                v-else
                link
                type="warning"
                size="small"
                :disabled="!!operating"
                :loading="operating === `${row.id}:role`"
                @click="handleSetRole(row, 'user')"
              >
                收回管理员
              </el-button>
              <el-button
                v-if="row.status === 'normal'"
                link
                type="danger"
                size="small"
                :disabled="!!operating"
                :loading="operating === `${row.id}:status`"
                @click="handleSetStatus(row, 'banned')"
              >
                封禁
              </el-button>
              <el-button
                v-else
                link
                type="success"
                size="small"
                :disabled="!!operating"
                :loading="operating === `${row.id}:status`"
                @click="handleSetStatus(row, 'normal')"
              >
                解封
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, jumper"
          background
          @current-change="loadUsers"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import request from '@/utils/request'

const userStore = useUserStore()

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const keyword = ref('')
const loading = ref(false)
// 正在进行的操作标记(`${id}:role` / `${id}:status`), 非空时全列按钮禁用防连点
const operating = ref(null)

// 管理员不能操作自己(后端也强制拦截), 自己那行只显示标签
const isSelf = (row) => row.id === userStore.userInfo?.id

// 后端返回本地 naive ISO(2026-11-26T22:04:50), 直接截取展示, 不做时区换算
const formatTime = (value) => (value ? value.replace('T', ' ').slice(0, 16) : '—')

const displayName = (row) => row.nickname || row.phone || `用户 #${row.id}`

const loadUsers = async () => {
  loading.value = true
  try {
    const res = await request.get('/admin/users', {
      params: {
        keyword: keyword.value || undefined,
        page: page.value,
        page_size: pageSize,
      },
    })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    // 拦截器已统一提示
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  page.value = 1
  loadUsers()
}

// 设为/收回管理员: 先二次确认, 成功后就地刷新当前页
const handleSetRole = async (row, role) => {
  const isPromote = role === 'admin'
  const tip = isPromote
    ? `确定将「${displayName(row)}」设为管理员吗？之后该账号只能访问管理端页面。`
    : `确定收回「${displayName(row)}」的管理员权限吗？之后恢复为普通求职者账号。`
  try {
    await ElMessageBox.confirm(tip, isPromote ? '设为管理员' : '收回管理员', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
  } catch (e) {
    return // 用户取消
  }

  operating.value = `${row.id}:role`
  try {
    await request.put(`/admin/users/${row.id}/role`, { role })
    ElMessage.success(isPromote ? '已设为管理员' : '已收回管理员权限')
    await loadUsers()
  } catch (e) {
    // 拦截器已统一提示
  } finally {
    operating.value = null
  }
}

// 封禁/解封: 同上
const handleSetStatus = async (row, status) => {
  const isBan = status === 'banned'
  const tip = isBan
    ? `确定封禁「${displayName(row)}」吗？封禁后该账号无法登录，在线会话下一步操作即失效。`
    : `确定解封「${displayName(row)}」吗？解封后该账号立即恢复正常登录。`
  try {
    await ElMessageBox.confirm(tip, isBan ? '封禁账号' : '解封账号', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
  } catch (e) {
    return
  }

  operating.value = `${row.id}:status`
  try {
    await request.put(`/admin/users/${row.id}/status`, { status })
    ElMessage.success(isBan ? '账号已封禁' : '账号已解封')
    await loadUsers()
  } catch (e) {
    // 拦截器已统一提示
  } finally {
    operating.value = null
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.users-card {
  margin-bottom: 16px;
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

.search-area {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input {
  width: 220px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
