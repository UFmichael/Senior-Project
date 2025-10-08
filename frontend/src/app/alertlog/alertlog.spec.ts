import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Alertlog } from './alertlog';

describe('Alertlog', () => {
  let component: Alertlog;
  let fixture: ComponentFixture<Alertlog>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Alertlog]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Alertlog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
