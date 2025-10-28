import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { StreamService } from '../services/stream.service';
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

export class Dashboard implements OnInit, OnDestroy {
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
  
  // New properties for video streaming
  streamUrl: string = '';
  isStreamActive: boolean = false;

  constructor(
    private router: Router,
    private streamService: StreamService
  ) {
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

  ngOnDestroy(): void {
    // Stop the stream when component is destroyed
    if (this.selectedCameraId && this.isStreamActive) {
      const streamId = this.selectedCameraId.toString();
      this.streamService.stopStream(streamId).subscribe({
        next: () => console.log('Stream stopped on component destroy'),
        error: (err) => console.error('Error stopping stream:', err)
      });
    }
  }

  selectCamera(id: number): void {
    // Stop previous stream if any
    if (this.selectedCameraId && this.isStreamActive) {
      const previousStreamId = this.selectedCameraId.toString();
      this.streamService.stopStream(previousStreamId).subscribe({
        next: () => console.log('Previous stream stopped'),
        error: (err) => console.error('Error stopping previous stream:', err)
      });
    }

    this.selectedCameraId = id;
    this.selectedCamera = this.cameras.find(c => c.id === id);
    console.log(`Camera selected: ${this.selectedCamera?.name}`);
    
    // Start new stream if camera is active
    if (this.selectedCamera?.status === 'active') {
      this.startVideoStream(id);
    } else {
      this.isStreamActive = false;
      this.streamUrl = '';
    }
  }

  startVideoStream(cameraId: number): void {
    const streamId = cameraId.toString();
    
    // Start the stream processing on backend
    this.streamService.startStream(streamId).subscribe({
      next: (response) => {
        console.log('Stream started:', response);
        this.streamUrl = this.streamService.getStreamFeedUrl(streamId);
        this.isStreamActive = true;
      },
      error: (error) => {
        console.error('Error starting stream:', error);
        this.isStreamActive = false;
      }
    });
  }

  //place holder...
  viewEvent(event: Event): void {
    console.log(`Viewing event details for: ${event.type} at ${event.location}`);
  }

  goToAlertLog() {
    this.router.navigate(['/alertlog']);
  }

  goToAnalytics(): void {
    this.router.navigate(['/analytic'])
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