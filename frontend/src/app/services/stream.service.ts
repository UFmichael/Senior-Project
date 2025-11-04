import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, throwError } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';

interface StreamResponse {
  status: string;
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class StreamService {
  private apiUrl = 'http://localhost:8000/stream';
  
  private streamStatusSubject = new BehaviorSubject<boolean>(false);
  public streamStatus$ = this.streamStatusSubject.asObservable();
  
  // Track active streams
  private activeStreams = new Map<string, boolean>();

  constructor(private http: HttpClient) {}

  /**
   * Start the video stream handler
   * Matches backend endpoint: POST /stream/{stream_id}/start
   */
  startStream(streamId: string): Observable<StreamResponse> {
    const headers = this.getAuthHeaders();
    
    return this.http.post<StreamResponse>(
      `${this.apiUrl}/${streamId}/start`, 
      {}, 
      { headers }
    ).pipe(
      tap((response) => {
        console.log('Stream started successfully:', response);
        this.activeStreams.set(streamId, true);
        this.streamStatusSubject.next(true);
      }),
      catchError((error) => {
        console.error('Stream service error:', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Stop the video stream handler
   * Matches backend endpoint: POST /stream/{stream_id}/stop
   */
  stopStream(streamId: string): Observable<StreamResponse> {
    const headers = this.getAuthHeaders();
    
    return this.http.post<StreamResponse>(
      `${this.apiUrl}/${streamId}/stop`, 
      {},
      { headers }
    ).pipe(
      tap((response) => {
        console.log('Stream stopped successfully:', response);
        this.activeStreams.delete(streamId);
        if (this.activeStreams.size === 0) {
          this.streamStatusSubject.next(false);
        }
      }),
      catchError((error) => {
        console.error('Failed to stop stream:', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Get the video feed URL for streaming
   * For MJPEG streams with authentication
   * 
   * IMPORTANT: Since img elements can't send Authorization headers,
   * and the backend requires header authentication, we have two options:
   * 
   * Option A: Use EventSource or fetch API to get frames with auth headers
   * Option B: Create a service worker to intercept img requests and add headers
   * Option C: Backend needs to support token in query params (simplest)
   * 
   * For now, returning URL with token as query param - backend needs minor update
   * to handle this, OR use the getAuthenticatedStreamBlob method below
   */
  getStreamFeedUrl(streamId: string, streamType: string = 'mjpeg'): string {
    // This URL structure expects the backend to handle token from query params
    // If backend doesn't support this, use getAuthenticatedStreamBlob instead
    const token = this.getAuthToken();
    const feedUrl = `${this.apiUrl}/${streamId}/feed`;
    
    // Note: This requires backend to accept token from query params
    // Otherwise, use the alternative method below
    return token ? `${feedUrl}?token=${encodeURIComponent(token)}` : feedUrl;
  }

  /**
   * Alternative: Fetch MJPEG stream with authentication headers
   * This method can be used if backend doesn't support query param tokens
   */
  getAuthenticatedStreamBlob(streamId: string): Observable<Blob> {
    const headers = this.getAuthHeaders();
    
    // Fetch the stream data with proper authentication
    return this.http.get(`${this.apiUrl}/${streamId}/feed`, {
      headers,
      responseType: 'blob'
    }).pipe(
      catchError((error) => {
        console.error('Failed to fetch stream:', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Check if a specific stream is running
   */
  isStreamRunning(streamId?: string): boolean {
    if (streamId) {
      return this.activeStreams.get(streamId) || false;
    }
    return this.streamStatusSubject.value;
  }

  /**
   * Get authentication token from localStorage
   */
  private getAuthToken(): string | null {
    return localStorage.getItem('access_token');
  }

  /**
   * Get authorization headers for API requests
   */
  private getAuthHeaders(): HttpHeaders {
    const token = this.getAuthToken();
    if (!token) {
      console.warn('No auth token found in localStorage');
      return new HttpHeaders({
        'Content-Type': 'application/json'
      });
    }
    
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    });
  }

  /**
   * Optional: Start recording the stream
   */
  startRecording(streamId: string): Observable<any> {
    const headers = this.getAuthHeaders();
    return this.http.post(`${this.apiUrl}/${streamId}/record/start`, {}, { headers })
      .pipe(
        catchError((error) => {
          console.warn('Recording endpoint not implemented in backend');
          return throwError(() => error);
        })
      );
  }

  /**
   * Optional: Stop recording the stream
   */
  stopRecording(streamId: string): Observable<any> {
    const headers = this.getAuthHeaders();
    return this.http.post(`${this.apiUrl}/${streamId}/record/stop`, {}, { headers })
      .pipe(
        catchError((error) => {
          console.warn('Recording endpoint not implemented in backend');
          return throwError(() => error);
        })
      );
  }
}