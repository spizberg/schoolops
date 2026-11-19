import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Dashboard } from '../../core/models';
import { DashboardPage } from './dashboard.page';

describe('DashboardPage', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DashboardPage],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it("renders counts and today's sessions", async () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();

    const dashboard: Dashboard = {
      active_year: {
        id: '11111111-1111-1111-1111-111111111111',
        label: '2026-2027',
        start_date: '2026-09-01',
        end_date: '2027-06-30',
        meeting_weekdays: [7],
        is_active: true,
        created_at: '',
        updated_at: '',
      },
      today: '2026-11-22',
      counts: { children: 12, volunteers: 3, classes: 4 },
      todays_sessions: [
        {
          id: '22222222-2222-2222-2222-222222222222',
          class_id: '33333333-3333-3333-3333-333333333333',
          class_name: 'Preschool',
          date: '2026-11-22',
          start_time: '09:00:00',
          end_time: '10:30:00',
          topic: 'Creation',
          volunteers: 2,
        },
      ],
      attendance_recorded_today: 11,
      not_seen_recently: 2,
    };
    http
      .expectOne((request) => request.url === '/v1/reports/dashboard')
      .flush(dashboard);
    await fixture.whenStable();
    await new Promise((resolve) => setTimeout(resolve, 0));
    http
      .expectOne((request) => request.url === '/v1/reports/not-seen')
      .flush({
        since: '2026-10-23',
        class_id: null,
        items: [
          {
            child: {
              id: '44444444-4444-4444-4444-444444444444',
              first_name: 'Grace',
              last_name: 'Hopper',
              date_of_birth: '2018-03-14',
              allergies: null,
              medical_notes: null,
              photo_consent: 'not_recorded',
              status: 'active',
            },
            last_present_on: null,
            missed_sessions: 2,
          },
        ],
        total: 1,
      });
    await fixture.whenStable();
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('12');
    expect(text).toContain('Active children');
    expect(text).toContain('Not seen in 30 days');
    expect(text).toContain('Creation');
    expect(text).toContain('Preschool');
  });
});
