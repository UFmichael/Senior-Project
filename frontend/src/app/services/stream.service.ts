import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

interface StreamResponse {
  status: string;
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class StreamService {
  private apiUrl = environment.apiUrl ? `${environment.apiUrl}/stream` : 'http://localhost:8000/stream';
  
  private streamStatusSubject = new BehaviorSubject<boolean>(false);
  public streamStatus$ = this.streamStatusSubject.asObservable();

  constructor(private http: HttpClient) {}

  /**
   * Start the video stream handler
   */
  startStream(streamId: string): Observable<StreamResponse> {
    return this.http.post<StreamResponse>(`${this.apiUrl}/${streamId}/start`, {})
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
    return this.http.post<StreamResponse>(`${this.apiUrl}/${streamId}/stop`, {})
      .pipe(
        tap(() => this.streamStatusSubject.next(false)),
        catchError(error => {
          console.error('Failed to stop stream:', error);
          throw error;
        })
      );
  }

  /**
   * Get current stream status
   */
  isStreamRunning(): boolean {
    return this.streamStatusSubject.value;
  }

  getStreamFeedUrl(streamId: string): string {
    const token = localStorage.getItem('auth_token');
    
    if (token) {
      return `${this.apiUrl}/${streamId}/feed?token=${token}`;
    }
    
    return `${this.apiUrl}/${streamId}/feed`;
  }

  getStreamFeedUrlWithAuth(streamId: string): string {
    return `${this.apiUrl}/${streamId}/feed`;
  }

  getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('auth_token');
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
  }
}