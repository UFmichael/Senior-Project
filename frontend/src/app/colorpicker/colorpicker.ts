import { Component, OnInit } from '@angular/core';
import { CommonModule, AsyncPipe } from '@angular/common';
import { ColorOption, Colormenu } from '../colormenu/colormenu';
import { Observable } from 'rxjs';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-colorpicker',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './colorpicker.html',
  styleUrl: './colorpicker.css'
})

export class Colorpicker implements OnInit {
  colors: ColorOption[] = [];
  currentColor$!: Observable<ColorOption>;

  constructor(private color: Colormenu) {}

  ngOnInit(): void {
    this.colors = this.color.colors;
    this.currentColor$ = this.color.currentColor$;
  }

  onColorChange(cssClass: string): void {
    const selectedColor = this.colors.find(c => c.cssClass === cssClass);
    if (selectedColor) {
      this.color.selectColor(selectedColor);
    }
  }
}
