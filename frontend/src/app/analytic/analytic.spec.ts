import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Analytic } from './analytic';

describe('Analytic', () => {
  let component: Analytic;
  let fixture: ComponentFixture<Analytic>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Analytic]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Analytic);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
