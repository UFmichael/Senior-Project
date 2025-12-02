import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./login/login').then(m => m.Login) },
  { path: 'signup', loadComponent: () => import('./signup/signup').then(m => m.Signup) },
  { 
    path: 'dashboard', 
    loadComponent: () => import('./dashboard/dashboard').then(m => m.Dashboard),
    canActivate: [authGuard]
  },
  { 
    path: 'analytic', 
    loadComponent: () => import('./analytic/analytic').then(m => m.Analytic),
    canActivate: [authGuard]
  },
  { 
    path: 'alertlog', 
    loadComponent: () => import('./alertlog/alertlog').then(m => m.Alertlog),
    canActivate: [authGuard]
  },
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: '**', redirectTo: '/login' }
];