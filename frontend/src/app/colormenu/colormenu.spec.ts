import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Colormenu } from './colormenu';

describe('Colormenu', () => {
  let component: Colormenu;
  let fixture: ComponentFixture<Colormenu>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Colormenu]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Colormenu);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
