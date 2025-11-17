import { Component, OnInit, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { StreamService } from '../services/stream.service';
import { Colorpicker } from '../colorpicker/colorpicker';
import { Subscription } from 'rxjs';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';

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

interface Detection {
  class: string;
  confidence: number;
  bbox: number[];
  timestamp?: string;
}

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, Colorpicker],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})

export class Dashboard implements OnInit, OnDestroy {
  @ViewChild('videoPlaceholder') videoPlaceholder!: ElementRef;

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

  // NEW: Video stream properties
  currentFrame: SafeUrl | null = null;
  private previousFrameUrl: string | null = null; // Track for cleanup
  currentDetections: Detection[] = [];
  private frameSubscription?: Subscription;
  isStreamActive: boolean = false;

  constructor(
    private router: Router,
    private streamService: StreamService,
    private sanitizer: DomSanitizer
  ) 
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

    // Subscribe to frame updates from WebSocket
    this.frameSubscription = this.streamService.frame$.subscribe({
      next: (data) => {
        // Clean up old object URL to prevent memory leaks
        if (this.previousFrameUrl) {
          URL.revokeObjectURL(this.previousFrameUrl);
        }
        
        // Store the new URL for future cleanup
        this.previousFrameUrl = data.frame;
        this.currentFrame = this.sanitizer.bypassSecurityTrustUrl(data.frame);
        this.currentDetections = data.detections;
      },
      error: (err) => {
        console.error('Error receiving frame:', err);
      }
    });
  }

  ngOnDestroy(): void {
    // Clean up subscriptions and WebSocket connection
    if (this.frameSubscription) {
      this.frameSubscription.unsubscribe();
    }
    
    // Clean up object URL
    if (this.previousFrameUrl) {
      URL.revokeObjectURL(this.previousFrameUrl);
    }

    // Disconnect WebSocket
    this.streamService.disconnectWebSocket();
  }

  selectCamera(id: number): void {
    this.selectedCameraId = id;
    this.selectedCamera = this.cameras.find(c => c.id === id);
    console.log(`Camera selected: ${this.selectedCamera?.name}`);

    // Disconnect from previous stream
    this.streamService.disconnectWebSocket();
    
    // Clean up old frame URL
    if (this.previousFrameUrl) {
      URL.revokeObjectURL(this.previousFrameUrl);
      this.previousFrameUrl = null;
    }
    
    this.currentFrame = null;
    this.currentDetections = [];

    // Connect to new stream if camera is active
    if (this.selectedCamera && this.selectedCamera.status === 'active') {
      const streamId = this.selectedCamera.id.toString();
      this.streamService.connectToStream(streamId);
    }
  }

  /**
   * Start streaming for the selected camera
   */
  startStreaming(): void {
    if (!this.selectedCamera) {
      console.error('No camera selected');
      return;
    }

    const streamId = this.selectedCamera.id.toString();
    
    this.streamService.startStream(streamId).subscribe({
      next: (response) => {
        console.log('Stream started:', response);
        this.isStreamActive = true;
        this.selectedCamera!.status = 'active';
        
        // Connect to WebSocket to receive frames
        this.streamService.connectToStream(streamId);
      },
      error: (err) => {
        console.error('Failed to start stream:', err);
        alert('Failed to start stream. Please try again.');
      }
    });
  }

  /**
   * Stop streaming for the selected camera
   */
  stopStreaming(): void {
    if (!this.selectedCamera) {
      console.error('No camera selected');
      return;
    }

    const streamId = this.selectedCamera.id.toString();
    
    this.streamService.stopStream(streamId).subscribe({
      next: (response) => {
        console.log('Stream stopped:', response);
        this.isStreamActive = false;
        this.selectedCamera!.status = 'offline';
        
        // Clean up frame URL
        if (this.previousFrameUrl) {
          URL.revokeObjectURL(this.previousFrameUrl);
          this.previousFrameUrl = null;
        }
        
        this.currentFrame = null;
        this.currentDetections = [];
      },
      error: (err) => {
        console.error('Failed to stop stream:', err);
        alert('Failed to stop stream. Please try again.');
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

  toggleFullscreen() {
    if (!this.videoPlaceholder) {
      console.error('Video placeholder element not found.');
      return;
    }

    const elem = this.videoPlaceholder.nativeElement as any;
    const doc = document as any;

    if (
      !doc.fullscreenElement &&
      !doc.webkitFullscreenElement &&
      !doc.mozFullScreenElement &&
      !doc.msFullscreenElement
    ) {
      if (elem.requestFullscreen) {
        elem.requestFullscreen();
      } else if (elem.webkitRequestFullscreen) {
        elem.webkitRequestFullscreen();
      } else if (elem.mozRequestFullScreen) {
        elem.mozRequestFullScreen();
      } else if (elem.msRequestFullscreen) {
        elem.msRequestFullscreen();
      }
    } else {
      if (doc.exitFullscreen) {
        doc.exitFullscreen();
      } else if (doc.webkitExitFullscreen) {
        doc.webkitExitFullscreen();
      } else if (doc.mozCancelFullScreen) {
        doc.mozCancelFullScreen();
      } else if (doc.msExitFullscreen) {
        doc.msExitFullscreen();
      }
    }
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

  /**
   * Get detection count for display
   */
  get detectionCount(): number {
    return this.currentDetections.length;
  }

  /**
   * Check if frame is available
   */
  get hasFrame(): boolean {
    return this.currentFrame !== null;
  }
}