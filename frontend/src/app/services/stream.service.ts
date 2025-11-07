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
          this.disconnectWebSocket();
        }),
        catchError(error => {
          console.error('Failed to stop stream:', error);
          throw error;
        })
      );
  }

  /**
   * Connect to WebSocket for receiving frames
   */
  connectToStream(streamId: string): void {
    if (this.ws) {
      console.log('WebSocket already connected');
      return;
    }

    const wsPath = `${this.wsUrl}/stream/${streamId}/ws`;
    console.log(`Connecting to WebSocket: ${wsPath}`);
    
    this.ws = new WebSocket(wsPath);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      // Send ping to keep connection alive
      this.sendPing();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'frame' && data.frame) {
          // Decode base64 frame data
          const binaryString = atob(data.frame);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          
          const blob = new Blob([bytes], { type: 'image/jpeg' });
          const imageUrl = URL.createObjectURL(blob);
          
          this.frameSubject.next({
            frame: imageUrl,
            detections: data.detections || []
          });
        }
      } catch (e) {
        // Ignore non-JSON messages (like "pong" responses)
        if (event.data !== 'pong') {
          console.error('Error processing message:', e);
        }
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.ws = null;
    };

    // Send periodic pings to keep connection alive
    setInterval(() => {
      this.sendPing();
    }, 30000); // Every 30 seconds
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      console.log('WebSocket disconnected');
    }
  }

  /**
   * Send ping to keep connection alive
   */
  private sendPing(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send('ping');
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