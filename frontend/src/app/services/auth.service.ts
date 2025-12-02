import { Injectable, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, BehaviorSubject, throwError } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface UserResponse {
  id: string;
  username?: string;
  disabled?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'http://localhost:8000';
  private tokenKey = 'access_token';
  private refreshTokenKey = 'refresh_token';
  private isBrowser: boolean;

  private currentUserSubject = new BehaviorSubject<UserResponse | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(
    private http: HttpClient,
    private router: Router,
    @Inject(PLATFORM_ID) platformId: Object
  ) {
    this.isBrowser = isPlatformBrowser(platformId);

    if (this.isBrowser && this.getToken()) {
      this.loadCurrentUser();
    }
  }

  /**
   * Login with username and password
   * Sends x-www-form-urlencoded data to FastAPI /token
   */
  login(username: string, password: string): Observable<TokenResponse> {
    const body = new HttpParams()
      .set('username', username)
      .set('password', password);

    const headers = new HttpHeaders({
      'Content-Type': 'application/x-www-form-urlencoded'
    });

    return this.http.post<TokenResponse>(`${this.apiUrl}/auth/token`, body.toString(), { headers })
      .pipe(
        tap(response => {
          this.setToken(response.access_token);
          this.setRefreshToken(response.refresh_token);
        }),
        catchError(error => {
          console.error('Login failed:', error);
          return throwError(() => error);
        })
      );
  }

  /**
   * Refresh access token using refresh token
   */
  refreshToken(): Observable<any> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      return throwError(() => new Error('No refresh token available'));
    }

    return this.http.post(`${this.apiUrl}/token/refresh`, {
      refresh_token: refreshToken
    }).pipe(
      tap((response: any) => {
        this.setToken(response.access_token);
      }),
      catchError(error => {
        this.logout();
        return throwError(() => error);
      })
    );
  }

  /**
   * Load current user info
   */
  loadCurrentUser(): void {
  if (!this.isBrowser) return;

  this.http.get<UserResponse>(`${this.apiUrl}/users/me`)
    .subscribe({
      next: (user) => this.currentUserSubject.next(user),
      error: (error) => {
        console.error('Failed to load user:', error);
        if (error.status === 401) {
          this.logout();
        }
      }
    });
}

  /**
   * Logout user
   */
  logout(): void {
    if (this.isBrowser) {
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem(this.refreshTokenKey);
      localStorage.removeItem('token');
    }
    this.currentUserSubject.next(null);
    this.router.navigate(['/login']);
  }

  /**
   * Check if logged in
   */
  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  /**
   * Token getters/setters
   */
  getToken(): string | null {
    if (!this.isBrowser) return null;
    return localStorage.getItem(this.tokenKey);
  }

  getRefreshToken(): string | null {
    if (!this.isBrowser) return null;
    return localStorage.getItem(this.refreshTokenKey);
  }

  private setToken(token: string): void {
    if (!this.isBrowser) return;
    localStorage.setItem(this.tokenKey, token);
  }

  private setRefreshToken(token: string): void {
    if (!this.isBrowser) return;
    localStorage.setItem(this.refreshTokenKey, token);
  }
}