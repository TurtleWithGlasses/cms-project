import { useEffect, useRef, useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { wsService } from '../services/websocket'

/**
 * React hook for WebSocket integration.
 *
 * Connects to the WebSocket server, subscribes to channels,
 * and can invalidate React Query caches on events.
 *
 * @param {Object} options
 * @param {string[]} [options.channels] - Channels to subscribe to
 * @param {Object} [options.onEvent] - Event handlers { 'event.type': (data) => {} }
 * @param {boolean} [options.autoInvalidate] - Auto-invalidate queries on content/comment events
 * @returns {{ isConnected: boolean, lastEvent: Object|null }}
 */
export function useWebSocket({ channels = [], onEvent = {}, autoInvalidate = true } = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState(null)
  const queryClient = useQueryClient()
  const cleanupRef = useRef([])

  useEffect(() => {
    // Connect with token from localStorage
    const token = localStorage.getItem('access_token')
    wsService.connect(token)

    // Track connection status
    const unsubConnection = wsService.on('connection', ({ status }) => {
      setIsConnected(status === 'connected')
    })
    cleanupRef.current.push(unsubConnection)

    // Subscribe to channels
    channels.forEach((channel) => wsService.subscribe(channel))

    // Auto-invalidate on content events
    if (autoInvalidate) {
      const contentEvents = ['content.created', 'content.updated', 'content.deleted', 'content.published']
      contentEvents.forEach((eventType) => {
        const unsub = wsService.on(eventType, (data) => {
          setLastEvent({ type: eventType, data, timestamp: Date.now() })
          queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          queryClient.invalidateQueries({ queryKey: ['content'] })
        })
        cleanupRef.current.push(unsub)
      })

      const commentEvents = ['comment.created', 'comment.approved', 'comment.deleted']
      commentEvents.forEach((eventType) => {
        const unsub = wsService.on(eventType, (data) => {
          setLastEvent({ type: eventType, data, timestamp: Date.now() })
          queryClient.invalidateQueries({ queryKey: ['comments'] })
        })
        cleanupRef.current.push(unsub)
      })
    }

    // Register custom event handlers
    Object.entries(onEvent).forEach(([eventType, handler]) => {
      const unsub = wsService.on(eventType, handler)
      cleanupRef.current.push(unsub)
    })

    // Cleanup on unmount
    return () => {
      cleanupRef.current.forEach((unsub) => unsub())
      cleanupRef.current = []
      channels.forEach((channel) => wsService.unsubscribe(channel))
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { isConnected, lastEvent }
}

export default useWebSocket
