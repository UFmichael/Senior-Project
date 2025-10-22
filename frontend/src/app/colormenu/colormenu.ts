import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable }  from 'rxjs';

export interface ColorOption {
  name: string;
  cssClass: string;
}

@Injectable({
  providedIn: 'root'
})

export class Colormenu {

  private readonly availableColors: ColorOption[] = [
    {name: 'Dark Blue', cssClass: 'blue-mode'},
    {name: 'Dark Mode', cssClass: 'dark-mode'},
    {name: 'Light Mode', cssClass: 'light-mode'}
  ];

private currentColor: BehaviorSubject<ColorOption>;

constructor() {
  const savedClass = localStorage.getItem('app-theme');
  const initialColor = this.availableColors.find(c => c.cssClass === savedClass) || this.availableColors[2];

  this.currentColor = new BehaviorSubject<ColorOption>(initialColor);
  this.applyTheme(initialColor.cssClass);
}

  get currentColor$(): Observable<ColorOption> {
    return this.currentColor.asObservable();
  }

  get colors(): ColorOption[] {
    return this.availableColors;
  }

  selectColor(color: ColorOption): void {
    this.currentColor.next(color);
    localStorage.setItem('app-theme', color.cssClass);
    this.applyTheme(color.cssClass);
  }

  private applyTheme(className: string): void{
    const body = document.body;
    this.availableColors.forEach(c => {
      body.classList.remove(c.cssClass);
    })
    body.classList.add(className);
  }
}

