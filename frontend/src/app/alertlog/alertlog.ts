import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon'
import { Colorpicker } from '../colorpicker/colorpicker';

@Component({
  selector: 'app-alertlog',
  imports: [MatIconModule, Colorpicker],
  templateUrl: './alertlog.html',
  styleUrl: './alertlog.css'
})
export class Alertlog {
  constructor(private router: Router) {}

  goDashboard() {
    this.router.navigate(['/dashboard']);
  }
}
