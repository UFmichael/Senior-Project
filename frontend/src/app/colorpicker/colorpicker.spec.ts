import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Colorpicker } from './colorpicker';

describe('Colorpicker', () => {
  let component: Colorpicker;
  let fixture: ComponentFixture<Colorpicker>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Colorpicker]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Colorpicker);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
