import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon'

@Component({
  selector: 'app-video',
  imports: [MatIconModule],
  templateUrl: './video.html',
  styleUrl: './video.css'
})
export class Video {
  constructor(private router: Router) {}

  goDashboard() {
    this.router.navigate(['/dashboard']);
  }
}
