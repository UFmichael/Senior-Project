import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Colorpicker } from '../colorpicker/colorpicker';

interface Camera {
  name: string;
  location: string;
  id: number;
  status: 'active' | 'offline' | 'warning';
}

interface Event {
  type: string;
  location: string;
  time: string;
  alertLevel: 'high' | 'warning' | 'info';
}

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, Colorpicker],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})

export class Dashboard {
  //dummy data...
  cameras: Camera[] = [
    { name: 'Main Entrance', location: 'Building A', id: 1, status: 'active' },
    { name: 'Side Entrance', location: 'Building B', id: 2, status: 'offline' }
  ]

  recentEvents: Event[] = [
    { type: 'Person detected', location: 'Main Entrance', time: '10:22 AM', alertLevel: 'high' },
    { type: 'Unusual activity', location: 'Main Entrance', time: '12:18 PM', alertLevel: 'warning' },
    { type: 'Crowd detected', location: 'Main Entrance', time: '10:15 AM', alertLevel: 'info' }
  ];

  selectedCameraId: number | null = null;
  selectedCamera: Camera | undefined;
  public currentTime: Date = new Date();

  constructor(private router: Router) 
  {
    setInterval(() => {
      this.currentTime = new Date();
    }, 1000);
  }

  get currentLiveStatusText(): string {
    if (!this.selectedCamera) return 'No Feed';
    if (this.selectedCamera.status === 'active') return '● LIVE';
    if (this.selectedCamera.status === 'warning') return '⚠ WARNING';
    if (this.selectedCamera.status === 'offline') return '■ OFFLINE';
    return '';
  }

  get currentLiveStatusClass(): string {
    if (!this.selectedCamera) return 'indicator-default';
    return 'indicator-' + this.selectedCamera.status;
  }

  ngOnInit(): void {
    if (this.cameras.length > 0) {
      this.selectCamera(this.cameras[0].id);
    }
  }

  selectCamera(id: number): void {
    this.selectedCameraId = id;
    this.selectedCamera = this.cameras.find(c => c.id === id);
    console.log(`Camera selected: ${this.selectedCamera?.name}`);
  }

  //place holder...
  viewEvent(event: Event): void {
    console.log(`Viewing event details for: ${event.type} at ${event.location}`);
  }

  goToAnalytics(): void {
    this.router.navigate(['/analytic'])
  }

  goToAlertLog(): void {
    this.router.navigate(['/alertlog']);
  }

  getCameraStatusClass(status: string): string {
    switch (status) {
      case 'active':
        return 'status-active';
      case 'warning':
        return 'status-warning';
      case 'offline':
        return 'status-offline';
      default:
        return '';
    }
  }
}
