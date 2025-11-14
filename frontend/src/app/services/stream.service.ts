import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';

interface StreamResponse {
  status: string;
  message: string;
}

interface Detection {
  class: string;
  confidence: number;
  bbox: number[];
  timestamp?: string;
}

interface FrameData {
  type: string;
  stream_id: string;
  detections: Detection[];
}

@Injectable({
  providedIn: 'root'
})
export class StreamService {
  private apiUrl = 'http://localhost:8000';
  private wsUrl = 'ws://localhost:8000';
  
  private streamStatusSubject = new BehaviorSubject<boolean>(false);
  public streamStatus$ = this.streamStatusSubject.asObservable();

  // WebSocket connection
  private ws: WebSocket | null = null;
  private frameSubject = new Subject<{ frame: string, detections: Detection[] }>();
  public frame$ = this.frameSubject.asObservable();
  
  // Reconnection parameters
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private baseReconnectDelay = 1000; // Start with 1 second
  private maxReconnectDelay = 30000; // Max 30 seconds
  private reconnectTimer: any = null;
  private currentStreamId: string | null = null;
  private shouldReconnect = false;
  
  // Heartbeat parameters
  private pingInterval: any = null;
  private pongTimeout: any = null;
  private lastPongTime: number = 0;
  private pingIntervalMs = 30000; // 30 seconds
  private pongTimeoutMs = 10000; // 10 seconds to wait for pong

  constructor(private http: HttpClient) {}

  /**
   * Start the video stream handler
   */
  startStream(streamId: string): Observable<StreamResponse> {
    return this.http.post<StreamResponse>(`${this.apiUrl}/stream/${streamId}/start`, {})
      .pipe(
        tap(() => this.streamStatusSubject.next(true)),
        catchError(error => {
          console.error('Failed to start stream:', error);
          throw error;
        })
      );
  }

  /**
   * Stop the video stream handler
   */
  stopStream(streamId: string): Observable<StreamResponse> {
    return this.http.post<StreamResponse>(`${this.apiUrl}/stream/${streamId}/stop`, {})
      .pipe(
        tap(() => {
          this.streamStatusSubject.next(false);
          this.shouldReconnect = false; // Prevent reconnection
          this.disconnectWebSocket();
        }),
        catchError(error => {
          console.error('Failed to stop stream:', error);
          throw error;
        })
      );
  }

  /**
   * Connect to WebSocket for receiving frames with automatic reconnection
   */
  connectToStream(streamId: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    this.currentStreamId = streamId;
    this.shouldReconnect = true;
    this.reconnectAttempts = 0;
    this._connectWebSocket(streamId);
  }

  /**
   * Internal method to establish WebSocket connection
   */
  private _connectWebSocket(streamId: string): void {
    const wsPath = `${this.wsUrl}/stream/${streamId}/ws`;
    console.log(`Connecting to WebSocket: ${wsPath} (attempt ${this.reconnectAttempts + 1})`);
    
    try {
      this.ws = new WebSocket(wsPath);
      
      // Store pending metadata for next frame
      let pendingMetadata: any = null;

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0; // Reset on successful connection
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        // Handle both text (JSON metadata) and binary (frame) messages
        if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'ping') {
              // Respond to ping
              this.sendMessage({ type: 'pong', timestamp: Date.now() });
            } else if (data.type === 'metadata') {
              // Store metadata for next binary frame
              pendingMetadata = data;
            }
          } catch (e) {
            console.warn('Received non-JSON text message:', event.data);
          }
        } else if (event.data instanceof Blob) {
          // Binary frame data - create object URL
          const imageUrl = URL.createObjectURL(event.data);
          
          this.frameSubject.next({
            frame: imageUrl,
            detections: pendingMetadata?.detections || []
          });
          
          // Clear pending metadata after use
          pendingMetadata = null;
        }
        
        // Update last pong time on any message
        this.lastPongTime = Date.now();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = (event) => {
        console.log(`WebSocket closed (code: ${event.code}, reason: ${event.reason})`);
        this.stopHeartbeat();
        this.ws = null;
        
        // Attempt reconnection with exponential backoff
        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          const delay = this.calculateBackoffDelay();
          console.log(`Reconnecting in ${delay}ms...`);
          
          this.reconnectTimer = setTimeout(() => {
            this.reconnectAttempts++;
            if (this.currentStreamId) {
              this._connectWebSocket(this.currentStreamId);
            }
          }, delay);
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          console.error('Max reconnection attempts reached. Please refresh the page.');
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      
      // Retry with backoff
      if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
        const delay = this.calculateBackoffDelay();
        this.reconnectTimer = setTimeout(() => {
          this.reconnectAttempts++;
          this._connectWebSocket(streamId);
        }, delay);
      }
    }
  }

  /**
   * Calculate exponential backoff delay with jitter
   */
  private calculateBackoffDelay(): number {
    const exponentialDelay = Math.min(
      this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );
    
    // Add jitter (±25%) to prevent thundering herd
    const jitter = exponentialDelay * 0.25 * (Math.random() - 0.5);
    return Math.floor(exponentialDelay + jitter);
  }

  /**
   * Start heartbeat mechanism
   */
  private startHeartbeat(): void {
    this.stopHeartbeat(); // Clear any existing intervals
    this.lastPongTime = Date.now();
    
    // Send periodic pings
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        // Check if we received a pong recently
        const timeSinceLastPong = Date.now() - this.lastPongTime;
        
        if (timeSinceLastPong > this.pingIntervalMs + this.pongTimeoutMs) {
          console.warn('No pong received, connection may be dead. Reconnecting...');
          this.reconnectWebSocket();
        } else {
          this.sendMessage({ type: 'ping', timestamp: Date.now() });
        }
      }
    }, this.pingIntervalMs);
  }

  /**
   * Stop heartbeat mechanism
   */
  private stopHeartbeat(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    if (this.pongTimeout) {
      clearTimeout(this.pongTimeout);
      this.pongTimeout = null;
    }
  }

  /**
   * Force reconnection
   */
  private reconnectWebSocket(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    if (this.currentStreamId && this.shouldReconnect) {
      this.reconnectAttempts = 0;
      this._connectWebSocket(this.currentStreamId);
    }
  }

  /**
   * Send a message through WebSocket
   */
  private sendMessage(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket(): void {
    this.shouldReconnect = false;
    this.currentStreamId = null;
    
    // Clear reconnection timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      console.log('WebSocket disconnected');
    }
  }

  /**
   * Get current stream status
   */
  isStreamRunning(): boolean {
    return this.streamStatusSubject.value;
  }

  /**
   * Check if WebSocket is connected
   */
  isWebSocketConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
