import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

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


export class Dashboard implements OnInit{
  /*dummy data...*/
  recentAlerts: Status[] = [
    { timestamp: 'Time Stamp', level: 'Low' },
    { timestamp: 'Time Stamp', level: 'Low' },
    { timestamp: 'Time Stamp', level: 'Mid' },
    { timestamp: 'Time Stamp', level: 'Mid' },
    { timestamp: 'Time Stamp', level: 'High' },
  ];

  constructor(private router: Router) {}

  ngOnInit(): void {

  }

  goAlerts() {
    this.router.navigate(['/alertlog']);
  }

  goCamera() {
    this.router.navigate(['/video']);
  }
}
