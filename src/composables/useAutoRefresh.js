import { ref, onUnmounted } from 'vue'

/**
 * 管理后台自动刷新 composable
 * @param {Function} fetchFn - 刷新数据的函数
 * @param {number} interval - 刷新间隔(ms)，默认30s
 */
export function useAutoRefresh(fetchFn, interval = 30000) {
  const timer = ref(null)

  function start() {
    stop()
    timer.value = setInterval(fetchFn, interval)
  }

  function stop() {
    if (timer.value) {
      clearInterval(timer.value)
      timer.value = null
    }
  }

  onUnmounted(stop)

  return { start, stop }
}
