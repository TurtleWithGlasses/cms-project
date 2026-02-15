/**
 * WebSocket Service
 *
 * Manages WebSocket connection for real-time updates.
 * Supports channel subscriptions, auto-reconnect, and heartbeats.
 */

const WS_RECONNECT_DELAY = 3000
const WS_HEARTBEAT_INTERVAL = 30000
const WS_MAX_RECONNECT_ATTEMPTS = 10

class WebSocketService {
  constructor() {
    this._ws = null
    this._listeners = new Map()
    this._reconnectAttempts = 0
    this._heartbeatTimer = null
    this._reconnectTimer = null
    this._channels = new Set()
    this._connected = false
  }

  /**
   * Connect to the WebSocket server.
   * @param {string} [token] - JWT token for authenticated connections
   */
  connect(token) {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = token
      ? `${protocol}//${host}/api/v1/ws?token=${token}`
      : `${protocol}//${host}/api/v1/ws`

    try {
      this._ws = new WebSocket(url)
    } catch {
      this._scheduleReconnect(token)
      return
    }

    this._ws.onopen = () => {
      this._connected = true
      this._reconnectAttempts = 0
      this._startHeartbeat()

      // Re-subscribe to channels after reconnect
      this._channels.forEach((channel) => {
        this._send({ type: 'subscribe', channel })
      })

      this._emit('connection', { status: 'connected' })
    }

    this._ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        this._emit(message.type, message.data || message)
      } catch {
        // Ignore non-JSON messages
      }
    }

    this._ws.onclose = () => {
      this._connected = false
      this._stopHeartbeat()
      this._emit('connection', { status: 'disconnected' })
      this._scheduleReconnect(token)
    }

    this._ws.onerror = () => {
      // Error handling is done in onclose
    }
  }

  /**
   * Disconnect from the WebSocket server.
   */
  disconnect() {
    this._reconnectAttempts = WS_MAX_RECONNECT_ATTEMPTS // Prevent reconnect
    this._stopHeartbeat()
    clearTimeout(this._reconnectTimer)

    if (this._ws) {
      this._ws.close()
      this._ws = null
    }

    this._connected = false
    this._channels.clear()
    this._listeners.clear()
  }

  /**
   * Subscribe to a channel.
   * @param {string} channel - Channel name
   */
  subscribe(channel) {
    this._channels.add(channel)
    if (this._connected) {
      this._send({ type: 'subscribe', channel })
    }
  }

  /**
   * Unsubscribe from a channel.
   * @param {string} channel - Channel name
   */
  unsubscribe(channel) {
    this._channels.delete(channel)
    if (this._connected) {
      this._send({ type: 'unsubscribe', channel })
    }
  }

  /**
   * Register an event listener.
   * @param {string} eventType - Event type to listen for
   * @param {Function} callback - Callback function
   * @returns {Function} Unsubscribe function
   */
  on(eventType, callback) {
    if (!this._listeners.has(eventType)) {
      this._listeners.set(eventType, new Set())
    }
    this._listeners.get(eventType).add(callback)

    return () => {
      const listeners = this._listeners.get(eventType)
      if (listeners) {
        listeners.delete(callback)
      }
    }
  }

  /**
   * Check if connected.
   * @returns {boolean}
   */
  get isConnected() {
    return this._connected
  }

  // Private methods

  _send(data) {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(data))
    }
  }

  _emit(eventType, data) {
    const listeners = this._listeners.get(eventType)
    if (listeners) {
      listeners.forEach((cb) => cb(data))
    }
  }

  _startHeartbeat() {
    this._stopHeartbeat()
    this._heartbeatTimer = setInterval(() => {
      this._send({ type: 'ping' })
    }, WS_HEARTBEAT_INTERVAL)
  }

  _stopHeartbeat() {
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer)
      this._heartbeatTimer = null
    }
  }

  _scheduleReconnect(token) {
    if (this._reconnectAttempts >= WS_MAX_RECONNECT_ATTEMPTS) {
      return
    }

    this._reconnectAttempts++
    const delay = WS_RECONNECT_DELAY * Math.min(this._reconnectAttempts, 5)

    this._reconnectTimer = setTimeout(() => {
      this.connect(token)
    }, delay)
  }
}

// Singleton instance
export const wsService = new WebSocketService()
export default wsService
