import { Component, OnInit, ViewChild, ViewEncapsulation, AfterViewInit } from '@angular/core';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon'
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { Colorpicker } from '../colorpicker/colorpicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { MatSort, MatSortModule } from '@angular/material/sort';

export interface AlertLog {
    camera: string;
    type: string;
    location: string;
    time: string;
    alertLevel: 'High' | 'Warning' | 'Info';
}

//temp data... I don't have time to look into the DB... sorry
const ELEMENT_DATA: AlertLog[] = [
    { camera: 'Camera 1', type: 'Person detected', location: 'Main Entrance', time: '2025-11-30 09:30:15', alertLevel: 'High' },
    { camera: 'Camera 1', type: 'Crowd detected', location: 'Main Entrance', time: '2025-11-30 09:28:15', alertLevel: 'Info' },
    { camera: 'Camera 2', type: 'Unusual activity', location: 'Side Entrance', time: '2025-11-30 09:25:40', alertLevel: 'Warning' },
    { camera: 'Camera 2', type: 'Unusual activity', location: 'Side Entrance', time: '2025-11-30 09:20:00', alertLevel: 'Info' },
    { camera: 'Camera 1', type: 'Vehicle stopped', location: 'Main Entrance', time: '2025-11-30 09:15:30', alertLevel: 'Warning' },
    { camera: 'Camera 1', type: 'Crowd detected', location: 'Main Entrance', time: '2025-11-30 09:10:55', alertLevel: 'High' },
    { camera: 'Camera 1', type: 'Crowd detected', location: 'Main Entrance', time: '2025-11-30 09:05:22', alertLevel: 'Info' },
    { camera: 'Camera 2', type: 'Person detected', location: 'Side Entrance', time: '2025-11-30 09:02:05', alertLevel: 'Warning' },
    { camera: 'Camera 2', type: 'Crowd detected', location: 'Side Entrance', time: '2025-11-30 09:00:00', alertLevel: 'Info' },
    { camera: 'Camera 2', type: 'Unusual activity', location: 'Side Entrance', time: '2025-11-30 08:55:00', alertLevel: 'High' },
    { camera: 'Camera 1', type: 'Unusual activity', location: 'Main Entrance', time: '2025-11-30 08:50:00', alertLevel: 'Warning' },
];

@Component({
    selector: 'app-alertlog',
    imports: [MatIconModule, Colorpicker, MatFormFieldModule, MatInputModule, MatTableModule, MatPaginatorModule, MatButtonModule, MatCardModule, CommonModule, MatSortModule],
    templateUrl: './alertlog.html',
    styleUrl: './alertlog.css',
    encapsulation: ViewEncapsulation.None
})

export class Alertlog implements OnInit, AfterViewInit {
    
    displayedColumns: string[] = ['camera', 'type', 'location', 'time', 'alertLevel'];
    dataSource = new MatTableDataSource<AlertLog>(ELEMENT_DATA);

    @ViewChild(MatPaginator) paginator!: MatPaginator;
    @ViewChild(MatSort) sort!: MatSort;

    constructor(private router: Router) {}

    //I think the only thing needed is a function to retrieve the data from the DB... 

    goDashboard() {
        this.router.navigate(['/dashboard']);
    }

    ngOnInit() {
        this.dataSource.data.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());
        this.dataSource.sortingDataAccessor = (item, property) => {
            switch (property) {
                case 'alertLevel': return this.getAlertLevelValue(item.alertLevel);
                case 'time': return new Date(item.time).getTime();
                default: return item[property as keyof AlertLog];
            }
        };
    }

    ngAfterViewInit() {
        this.dataSource.paginator = this.paginator;
        this.dataSource.sort = this.sort;
    }

    getAlertLevelValue(level: 'High' | 'Warning' | 'Info'): number {
        switch (level) {
            case 'High': return 3;
            case 'Warning': return 2;
            case 'Info': return 1;
            default: return 0;
        }
    }
    
    applySearchFilter(event: Event) {
        const filterValue = (event.target as HTMLInputElement).value;
        
        this.dataSource.filterPredicate = (data: AlertLog, filter: string) => {
            const dataStr = Object.values(data).join(' ').toLowerCase();
            return dataStr.includes(filter);
        };
        
        this.dataSource.filter = filterValue.trim().toLowerCase();
        
        if (this.dataSource.paginator) {
            this.dataSource.paginator.firstPage();
        }
    }
}