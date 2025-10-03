import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { Login } from './login/login'
import { Signup } from './signup/signup'
import { Dashboard } from './dashboard/dashboard';
import { Alertlog } from './alertlog/alertlog'
import { Video } from './video/video'

export const routes: Routes = [
    {path: '', redirectTo: '/login', pathMatch: 'full'},
    {path: 'login', component: Login},
    {path: 'signup', component: Signup},
    {path: 'dashboard', component: Dashboard},
    {path: 'alertlog', component: Alertlog},
    {path: 'video', component: Video}
];

@NgModule({
    imports: [RouterModule.forRoot(routes)],
    exports: [RouterModule]
})

export class AppRoutingModule {}