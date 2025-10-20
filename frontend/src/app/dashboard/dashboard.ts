import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { StreamService } from '../services/stream.service';

interface Status {
  timestamp: string;
  level: 'Low' | 'Mid' | 'High';
}

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})

export class Dashboard implements OnInit, OnDestroy {

  cameraName: string = 'Camera Name';
  recentAlerts: Status[] = [];
  isStreamActive: boolean = false;

  constructor(
    private router: Router,
    private streamService: StreamService
  ) {}

  ngOnInit(): void {
    this.loadRecentAlerts();
  }

  ngOnDestroy(): void {
    if (this.isStreamActive) {
      this.stopStream();
    }
  }

  loadRecentAlerts(): void {
    // Dummy data for now
    this.recentAlerts = [
      { timestamp: new Date().toLocaleString(), level: 'Low' },
      { timestamp: new Date().toLocaleString(), level: 'Low' },
      { timestamp: new Date().toLocaleString(), level: 'Mid' },
      { timestamp: new Date().toLocaleString(), level: 'Mid' },
      { timestamp: new Date().toLocaleString(), level: 'High' },
    ];
  }

  startStream(): void {
    this.streamService.startStream().subscribe({
      next: (response) => {
        console.log('Stream started:', response);
        this.isStreamActive = true;
      },
      error: (error) => {
        console.error('Error starting stream:', error);
      }
    });
  }

  stopStream(): void {
    this.streamService.stopStream().subscribe({
      next: (response) => {
        console.log('Stream stopped:', response);
        this.isStreamActive = false;
      },
      error: (error) => {
        console.error('Error stopping stream:', error);
      }
    });
  }

  goAlerts() {
    this.router.navigate(['/alertlog']);
  }

  goCamera() {
    this.router.navigate(['/video']);
  }
}