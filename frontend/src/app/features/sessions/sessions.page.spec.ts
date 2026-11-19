import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { SessionsPage } from './sessions.page';

const CLASS_ID = '11111111-1111-1111-1111-111111111111';
const SESSION_ID = '22222222-2222-2222-2222-222222222222';
const CHILD_ID = '33333333-3333-3333-3333-333333333333';

describe('SessionsPage', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SessionsPage],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('renders a session and its attendance roster', async () => {
    const fixture = TestBed.createComponent(SessionsPage);
    fixture.detectChanges();

    http.expectOne((request) => request.url === '/v1/classes').flush({
      items: [
        {
          id: CLASS_ID,
          ministry_year_id: '44444444-4444-4444-4444-444444444444',
          name: 'Preschool',
          age_band: '3-5 years',
          age_min: 3,
          age_max: 5,
          lead_volunteer_id: null,
          room: null,
          capacity: null,
          curriculum: null,
          created_at: '',
          updated_at: '',
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    });
    http.expectOne((request) => request.url === '/v1/volunteers').flush({
      items: [],
      total: 0,
      limit: 100,
      offset: 0,
    });
    await fixture.whenStable();
    await new Promise((resolve) => setTimeout(resolve, 0));

    const session = {
      id: SESSION_ID,
      class_id: CLASS_ID,
      date: '2026-09-06',
      start_time: '09:00:00',
      end_time: '10:30:00',
      topic: 'Creation',
      notes: null,
      content_markdown: '# Creation',
      resources: [],
      created_at: '',
      updated_at: '',
    };
    http
      .expectOne(
        (request) =>
          request.url.startsWith(`/v1/classes/${CLASS_ID}/sessions`) &&
          request.method === 'GET',
      )
      .flush({ items: [session], total: 1, limit: 100, offset: 0 });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Creation');

    const pending = fixture.componentInstance.openAttendance(session);
    http
      .expectOne(
        (request) =>
          request.url.startsWith(`/v1/class-sessions/${SESSION_ID}/attendance`),
      )
      .flush({
        session,
        entries: [
          {
            child: {
              id: CHILD_ID,
              first_name: 'Grace',
              last_name: 'Hopper',
              date_of_birth: '2018-03-14',
              allergies: 'Peanuts',
              medical_notes: null,
              photo_consent: 'granted',
              status: 'active',
            },
            guardians: [],
            status: null,
            note: null,
            recorded: false,
          },
        ],
        visitors: [],
        summary: {
          present: 0,
          absent: 0,
          not_recorded: 1,
          recorded: 0,
          visitors_present: 0,
          visitors_absent: 0,
          rate: null,
        },
      });
    http
      .expectOne(
        (request) =>
          request.url.startsWith(`/v1/class-sessions/${SESSION_ID}/volunteers`),
      )
      .flush({ class_session_id: SESSION_ID, volunteers: [] });
    await pending;
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Grace Hopper');
    expect(compiled.textContent).toContain('Peanuts');
    expect(
      compiled.querySelectorAll(
        'section[aria-labelledby="attendance-title"] tbody tr',
      ),
    ).toHaveLength(1);
  });
});
