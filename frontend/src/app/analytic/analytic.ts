import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon'
import { Colorpicker } from '../colorpicker/colorpicker';

@Component({
  selector: 'app-analytic',
  imports: [MatIconModule, Colorpicker],
  templateUrl: './analytic.html',
  styleUrl: './analytic.css'
})
export class Analytic {
  constructor(private router: Router) {}

  goDashboard() {
    this.router.navigate(['/dashboard']);
  }
}
