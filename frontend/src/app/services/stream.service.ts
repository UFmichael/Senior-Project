import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class StreamService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  startStream(): Observable<any> {
    return this.http.post(`${this.apiUrl}/stream/start`, {});
  }

  stopStream(): Observable<any> {
    return this.http.post(`${this.apiUrl}/stream/stop`, {});
  }
}