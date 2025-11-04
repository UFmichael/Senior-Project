import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { StreamService } from '../services/stream.service';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Colorpicker } from '../colorpicker/colorpicker';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';

interface Camera {
  name: string;
  location: string;
  id: number;
  status: 'active' | 'offline' | 'warning';
  streamType?: 'hls' | 'webrtc' | 'mjpeg';
}

interface DashboardEvent {
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
export class Dashboard implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('videoElement') videoElement!: ElementRef<HTMLImageElement>;
  
  // Camera data
  cameras: Camera[] = [
    { name: 'Main Entrance', location: 'Building A', id: 1, status: 'active', streamType: 'mjpeg' },
    { name: 'Side Entrance', location: 'Building B', id: 2, status: 'offline', streamType: 'mjpeg' }
  ];

  recentEvents: DashboardEvent[] = [
    { type: 'Person detected', location: 'Main Entrance', time: '10:22 AM', alertLevel: 'high' },
    { type: 'Unusual activity', location: 'Main Entrance', time: '12:18 PM', alertLevel: 'warning' },
    { type: 'Crowd detected', location: 'Main Entrance', time: '10:15 AM', alertLevel: 'info' }
  ];

  selectedCameraId: number | null = null;
  selectedCamera: Camera | undefined;
  currentTime: Date = new Date();
  
  // Video streaming properties
  streamUrl: string = '';
  isStreamActive: boolean = false;
  isMuted: boolean = true;
  isRecording: boolean = false;
  
  // Metrics
  peopleCount: number = 12;
  alertsToday: number = 3;
  resolvedAlerts: number = 2;
  
  // Stream reconnection handling
  private timeUpdateInterval: any;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectTimeout: any;
  private streamReader: ReadableStreamDefaultReader<Uint8Array> | null = null;

  constructor(
    private router: Router,
    private streamService: StreamService,
    private sanitizer: DomSanitizer,
    private http: HttpClient
  ) {
    // Update time every second
    this.timeUpdateInterval = setInterval(() => {
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
    // Auto-select first active camera
    const firstActiveCamera = this.cameras.find(c => c.status === 'active');
    if (firstActiveCamera) {
      this.selectCamera(firstActiveCamera.id);
    }
  }

  ngAfterViewInit(): void {
    // Component view is initialized
  }

  ngOnDestroy(): void {
    // Cleanup
    if (this.timeUpdateInterval) {
      clearInterval(this.timeUpdateInterval);
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    
    this.stopCurrentStream();
  }

  selectCamera(id: number): void {
    // Stop previous stream if any
    if (this.selectedCameraId && this.isStreamActive) {
      this.stopCurrentStream();
    }

    this.selectedCameraId = id;
    this.selectedCamera = this.cameras.find(c => c.id === id);
    console.log(`Camera selected: ${this.selectedCamera?.name}`);
    
    // Reset reconnect attempts
    this.reconnectAttempts = 0;
    
    // Start new stream if camera is active
    if (this.selectedCamera?.status === 'active') {
      this.startVideoStream(id);
    } else {
      this.isStreamActive = false;
      this.streamUrl = '';
    }
  }

  private startVideoStream(cameraId: number): void {
    const streamId = cameraId.toString();

    this.streamService.startStream(streamId).subscribe({
      next: () => {
        console.log('Stream started successfully, activating stream display...');
        this.activateMJPEGStream(streamId);
      },
      error: (error) => {
        console.error('Error starting stream:', error);
        
        if (error.status === 401) {
          console.error('Authentication failed');
          this.router.navigate(['/login']);
          return;
        }

        // Stream already running - treat as success
        if (error.status === 400) {
          console.warn("Stream already running - attaching anyway");
          this.activateMJPEGStream(streamId);
          return;
        }

        this.handleStreamError();
      }
    });
  }

  /**
   * Activate MJPEG stream using fetch API with Authorization header
   */
  private async activateMJPEGStream(streamId: string): Promise<void> {
    this.isStreamActive = true;
    console.log('Activating MJPEG stream for camera:', streamId);
    
    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error('No auth token found');
      this.router.navigate(['/login']);
      return;
    }

    try {
      const headers = new Headers({
        'Authorization': `Bearer ${token}`
      });

      const response = await fetch(`http://localhost:8000/stream/${streamId}/feed`, {
        headers: headers
      });

      if (!response.ok) {
        if (response.status === 401) {
          console.error('Authentication failed - redirecting to login');
          this.router.navigate(['/login']);
          return;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Check content type
      const contentType = response.headers.get('content-type');
      console.log('Stream content-type:', contentType);

      if (!contentType || !contentType.includes('multipart/x-mixed-replace')) {
        console.error('Invalid content type for MJPEG stream:', contentType);
        this.handleStreamError();
        return;
      }

      // This is an MJPEG stream
      console.log('Connected to MJPEG stream successfully');
      
      // Read the stream
      const reader = response.body?.getReader();
      if (!reader) {
        console.error('No reader available');
        this.handleStreamError();
        return;
      }

      this.streamReader = reader;

      // Process the stream
      this.processMJPEGStream(reader);

    } catch (error) {
      console.error('Failed to activate MJPEG stream:', error);
      this.handleStreamError();
    }
  }

  /**
   * Process MJPEG stream chunks
   */
  private async processMJPEGStream(reader: ReadableStreamDefaultReader<Uint8Array>): Promise<void> {
    let buffer = new Uint8Array(0);
    
    try {
      while (this.isStreamActive) {
        const { done, value } = await reader.read();
        
        if (done) {
          console.log('Stream ended');
          break;
        }

        // Append new data to buffer
        const newBuffer = new Uint8Array(buffer.length + value.length);
        newBuffer.set(buffer);
        newBuffer.set(value, buffer.length);
        buffer = newBuffer;

        // Look for JPEG boundaries in the buffer
        // JPEG starts with 0xFF 0xD8 and ends with 0xFF 0xD9
        let startIdx = this.findJPEGStart(buffer);
        let endIdx = this.findJPEGEnd(buffer, startIdx);

        while (startIdx !== -1 && endIdx !== -1) {
          // Extract the JPEG image
          const jpegData = buffer.slice(startIdx, endIdx + 2);
          
          // Display the frame
          const blob = new Blob([jpegData], { type: 'image/jpeg' });
          this.displayFrame(blob);
          
          // Remove processed data from buffer
          buffer = buffer.slice(endIdx + 2);
          
          // Look for next frame
          startIdx = this.findJPEGStart(buffer);
          endIdx = this.findJPEGEnd(buffer, startIdx);
        }

        // Prevent buffer from growing too large
        if (buffer.length > 1024 * 1024 * 10) { // 10MB limit
          console.warn('Buffer too large, resetting');
          buffer = new Uint8Array(0);
        }
      }
    } catch (error) {
      console.error('Error processing MJPEG stream:', error);
      this.handleStreamError();
    } finally {
      reader.cancel();
      this.streamReader = null;
    }
  }

  /**
   * Find JPEG start marker (0xFF 0xD8)
   */
  private findJPEGStart(buffer: Uint8Array): number {
    for (let i = 0; i < buffer.length - 1; i++) {
      if (buffer[i] === 0xFF && buffer[i + 1] === 0xD8) {
        return i;
      }
    }
    return -1;
  }

  /**
   * Find JPEG end marker (0xFF 0xD9)
   */
  private findJPEGEnd(buffer: Uint8Array, startIdx: number): number {
    for (let i = startIdx + 2; i < buffer.length - 1; i++) {
      if (buffer[i] === 0xFF && buffer[i + 1] === 0xD9) {
        return i;
      }
    }
    return -1;
  }

  /**
   * Display a frame in the img element
   */
  private displayFrame(blob: Blob): void {
    if (!this.videoElement || !this.videoElement.nativeElement) {
      console.error('Video element not found');
      return;
    }

    const url = URL.createObjectURL(blob);
    const img = this.videoElement.nativeElement;
    const oldUrl = img.src;

    img.src = url;

    // Clean up old blob URL
    if (oldUrl && oldUrl.startsWith('blob:')) {
      // Delay cleanup to ensure smooth transition
      setTimeout(() => URL.revokeObjectURL(oldUrl), 100);
    }

    // Reset reconnect attempts on successful frame
    this.reconnectAttempts = 0;
  }

  private handleStreamError(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      this.reconnectTimeout = setTimeout(() => {
        if (this.selectedCameraId) {
          this.startVideoStream(this.selectedCameraId);
        }
      }, 3000);
    } else {
      console.error('Max reconnection attempts reached');
      this.isStreamActive = false;
    }
  }

  private stopCurrentStream(): void {
    // Stop processing flag
    this.isStreamActive = false;
    
    // Cancel the stream reader if active
    if (this.streamReader) {
      this.streamReader.cancel().catch(err => console.error('Error canceling stream:', err));
      this.streamReader = null;
    }
    
    // Clean up blob URL if exists
    if (this.videoElement && this.videoElement.nativeElement) {
      const src = this.videoElement.nativeElement.src;
      if (src && src.startsWith('blob:')) {
        URL.revokeObjectURL(src);
        this.videoElement.nativeElement.src = '';
      }
    }
    
    // Stop the stream on backend
    if (this.selectedCameraId) {
      const streamId = this.selectedCameraId.toString();
      this.streamService.stopStream(streamId).subscribe({
        next: () => console.log('Stream stopped'),
        error: (err) => console.error('Error stopping stream:', err)
      });
    }
    
    // Clear stream URL
    this.streamUrl = '';
  }

  // Video control methods
  handleVideoError(event: Event): void {
    console.error('Stream error:', event);
    this.handleStreamError();
  }

  onVideoMetadataLoaded(): void {
    console.log('Stream loaded successfully');
    this.reconnectAttempts = 0;
  }

  toggleFullscreen(): void {
    const element = this.videoElement?.nativeElement;
    if (!element) return;
    
    if (!document.fullscreenElement) {
      element.requestFullscreen().catch(err => {
        console.error('Error attempting to enable fullscreen:', err);
      });
    } else {
      document.exitFullscreen();
    }
  }

  toggleRecording(): void {
    this.isRecording = !this.isRecording;
    
    if (this.selectedCameraId) {
      const streamId = this.selectedCameraId.toString();
      
      if (this.isRecording) {
        this.streamService.startRecording(streamId).subscribe({
          next: () => console.log('Recording started'),
          error: (err) => {
            console.error('Error starting recording:', err);
            this.isRecording = false;
          }
        });
      } else {
        this.streamService.stopRecording(streamId).subscribe({
          next: () => console.log('Recording stopped'),
          error: (err) => console.error('Error stopping recording:', err)
        });
      }
    }
  }

  takeSnapshot(): void {
    const element = this.videoElement?.nativeElement as HTMLImageElement;
    if (!element) return;
    
    const canvas = document.createElement('canvas');
    canvas.width = element.naturalWidth || element.width;
    canvas.height = element.naturalHeight || element.height;
    
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(element, 0, 0);
      
      canvas.toBlob(blob => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `snapshot_camera${this.selectedCameraId}_${Date.now()}.jpg`;
          a.click();
          URL.revokeObjectURL(url);
        }
      }, 'image/jpeg');
    }
  }

  viewEvent(event: DashboardEvent): void {
    console.log(`Viewing event details for: ${event.type} at ${event.location}`);
  }

  goToAlertLog(): void {
    this.router.navigate(['/alertlog']);
  }

  goToAnalytics(): void {
    this.router.navigate(['/analytic']);
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