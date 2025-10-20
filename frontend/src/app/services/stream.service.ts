import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';

interface StreamResponse {
  status: string;
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class StreamService {
  private apiUrl = 'http://localhost:8000';
  
  private streamStatusSubject = new BehaviorSubject<boolean>(false);
  public streamStatus$ = this.streamStatusSubject.asObservable();

  constructor(private http: HttpClient) {}

  /**
   * Start the video stream handler
   */
  startStream(): Observable<StreamResponse> {
    return this.http.post<StreamResponse>(`${this.apiUrl}/start`, {})
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
  stopStream(): Observable<StreamResponse> {
    return this.http.post<StreamResponse>(`${this.apiUrl}/stop`, {})
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
}