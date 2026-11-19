import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import {
  FormArray,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { ApiService, errorMessage } from '../../core/api';
import {
  AttendanceReport,
  AttendanceStatus,
  ClassGroup,
  ClassSession,
  Page,
  ResourceLink,
  SessionAttendance,
  SessionGenerateResult,
  SessionVolunteer,
  Volunteer,
} from '../../core/models';

@Component({
  selector: 'app-sessions-page',
  imports: [ReactiveFormsModule],
  templateUrl: './sessions.page.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SessionsPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);

  readonly classes = signal<ClassGroup[]>([]);
  readonly volunteers = signal<Volunteer[]>([]);
  readonly sessions = signal<ClassSession[]>([]);
  readonly selectedSession = signal<ClassSession | null>(null);
  readonly attendance = signal<SessionAttendance | null>(null);
  readonly sessionVolunteers = signal<SessionVolunteer[]>([]);
  readonly selectedVolunteerIds = signal<string[]>([]);
  readonly report = signal<AttendanceReport | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly attendanceLoading = signal(false);
  readonly volunteersSaving = signal(false);
  readonly error = signal<string | null>(null);
  readonly message = signal<string | null>(null);
  readonly editingId = signal<string | null>(null);

  readonly filters = this.fb.nonNullable.group({
    class_id: ['', Validators.required],
    from: [''],
    to: [''],
  });

  readonly sessionForm = this.fb.group({
    date: this.fb.nonNullable.control('', Validators.required),
    start_time: this.fb.nonNullable.control('09:00', Validators.required),
    end_time: this.fb.nonNullable.control('10:30', Validators.required),
    topic: this.fb.nonNullable.control(''),
    notes: this.fb.nonNullable.control(''),
    content_markdown: this.fb.nonNullable.control(''),
    resources: this.fb.array([]),
  });

  readonly generateForm = this.fb.nonNullable.group({
    start_date: ['', Validators.required],
    end_date: ['', Validators.required],
    start_time: ['09:00', Validators.required],
    end_time: ['10:30', Validators.required],
    mon: false,
    tue: false,
    wed: false,
    thu: false,
    fri: false,
    sat: false,
    sun: true,
  });

  readonly reportForm = this.fb.nonNullable.group({
    from: ['', Validators.required],
    to: ['', Validators.required],
  });

  readonly attendanceForm = this.fb.group({
    records: this.fb.array([]),
    visitors: this.fb.array([]),
  });

  get resources(): FormArray {
    return this.sessionForm.controls.resources;
  }

  get attendanceRecords(): FormArray {
    return this.attendanceForm.controls.records;
  }

  get visitorRecords(): FormArray {
    return this.attendanceForm.controls.visitors;
  }

  ngOnInit(): void {
    void this.bootstrap();
  }

  async bootstrap(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const [classes, volunteers] = await Promise.all([
        firstValueFrom(this.api.get<Page<ClassGroup>>('/classes', { limit: 100 })),
        firstValueFrom(
          this.api.get<Page<Volunteer>>('/volunteers', { status: 'active', limit: 100 }),
        ),
      ]);
      this.classes.set(classes.items);
      this.volunteers.set(volunteers.items);
      if (classes.items.length > 0) {
        this.filters.patchValue({ class_id: classes.items[0].id });
        await this.loadSessions();
      }
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }

  async loadSessions(): Promise<void> {
    if (this.filters.invalid) {
      this.filters.markAllAsTouched();
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.message.set(null);
    this.selectedSession.set(null);
    this.attendance.set(null);
    this.sessionVolunteers.set([]);
    this.selectedVolunteerIds.set([]);
    this.report.set(null);
    this.attendanceRecords.clear();
    this.visitorRecords.clear();
    try {
      const page = await firstValueFrom(
        this.api.get<Page<ClassSession>>(
          `/classes/${this.filters.controls.class_id.value}/sessions`,
          {
            from: this.filters.controls.from.value,
            to: this.filters.controls.to.value,
            limit: 100,
          },
        ),
      );
      this.sessions.set(page.items);
      if (page.items.length > 0) {
        const first = page.items[0].date;
        const last = page.items[page.items.length - 1].date;
        this.reportForm.patchValue({
          from: this.reportForm.controls.from.value || first,
          to: this.reportForm.controls.to.value || last,
        });
        this.generateForm.patchValue({
          start_date: this.generateForm.controls.start_date.value || first,
          end_date: this.generateForm.controls.end_date.value || last,
        });
      }
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }

  async saveSession(): Promise<void> {
    if (this.sessionForm.invalid) {
      this.sessionForm.markAllAsTouched();
      return;
    }
    const classId = this.filters.controls.class_id.value;
    if (!classId) {
      this.error.set('Select a class first.');
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    this.message.set(null);
    const value = this.sessionForm.getRawValue();
    const resources: ResourceLink[] = (value.resources as ResourceLink[])
      .map((item) => ({ label: item.label.trim(), url: item.url.trim() }))
      .filter((item) => item.label !== '' && item.url !== '');
    const payload = {
      date: value.date,
      start_time: value.start_time,
      end_time: value.end_time,
      topic: value.topic.trim() || null,
      notes: value.notes.trim() || null,
      content_markdown: value.content_markdown.trim() || null,
      resources,
    };
    try {
      const editingId = this.editingId();
      if (editingId) {
        await firstValueFrom(
          this.api.patch<ClassSession>(`/class-sessions/${editingId}`, payload),
        );
      } else {
        await firstValueFrom(
          this.api.post<ClassSession>(`/classes/${classId}/sessions`, payload),
        );
      }
      this.cancelEdit();
      await this.loadSessions();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  startEdit(session: ClassSession): void {
    this.editingId.set(session.id);
    this.sessionForm.patchValue({
      date: session.date,
      start_time: session.start_time.slice(0, 5),
      end_time: session.end_time.slice(0, 5),
      topic: session.topic ?? '',
      notes: session.notes ?? '',
      content_markdown: session.content_markdown ?? '',
    });
    this.resources.clear();
    for (const resource of session.resources) {
      this.resources.push(this.resourceGroup(resource.label, resource.url));
    }
    this.message.set(null);
  }

  cancelEdit(): void {
    this.editingId.set(null);
    this.sessionForm.reset({
      date: '',
      start_time: '09:00',
      end_time: '10:30',
      topic: '',
      notes: '',
      content_markdown: '',
    });
    this.resources.clear();
  }

  addResource(): void {
    this.resources.push(this.resourceGroup());
  }

  removeResource(index: number): void {
    this.resources.removeAt(index);
  }

  async deleteSession(session: ClassSession): Promise<void> {
    if (!globalThis.confirm(`Delete the session on ${session.date}?`)) {
      return;
    }
    this.error.set(null);
    try {
      await firstValueFrom(this.api.delete(`/class-sessions/${session.id}`));
      await this.loadSessions();
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  async generateSessions(): Promise<void> {
    const classId = this.filters.controls.class_id.value;
    if (!classId || this.generateForm.invalid) {
      this.generateForm.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    this.message.set(null);
    const value = this.generateForm.getRawValue();
    const mapping: [number, boolean][] = [
      [1, value.mon],
      [2, value.tue],
      [3, value.wed],
      [4, value.thu],
      [5, value.fri],
      [6, value.sat],
      [7, value.sun],
    ];
    const weekdays = mapping.filter(([, checked]) => checked).map(([day]) => day);
    try {
      const result = await firstValueFrom(
        this.api.post<SessionGenerateResult>(`/classes/${classId}/sessions/generate`, {
          start_date: value.start_date,
          end_date: value.end_date,
          start_time: value.start_time,
          end_time: value.end_time,
          weekdays,
        }),
      );
      this.message.set(
        `Generated ${result.created} session(s); ${result.skipped} skipped.`,
      );
      await this.loadSessions();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  async openAttendance(session: ClassSession): Promise<void> {
    this.selectedSession.set(session);
    this.attendanceLoading.set(true);
    this.error.set(null);
    this.message.set(null);
    this.attendance.set(null);
    this.attendanceRecords.clear();
    this.visitorRecords.clear();
    try {
      const [attendance, volunteers] = await Promise.all([
        firstValueFrom(
          this.api.get<SessionAttendance>(`/class-sessions/${session.id}/attendance`),
        ),
        firstValueFrom(
          this.api.get<{ volunteers: SessionVolunteer[] }>(
            `/class-sessions/${session.id}/volunteers`,
          ),
        ),
      ]);
      this.applyAttendance(attendance);
      this.sessionVolunteers.set(volunteers.volunteers);
      this.selectedVolunteerIds.set(
        volunteers.volunteers.map((item) => item.volunteer_id),
      );
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.attendanceLoading.set(false);
    }
  }

  async saveAttendance(): Promise<void> {
    const session = this.selectedSession();
    if (!session) {
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    this.message.set(null);
    const raw = this.attendanceForm.getRawValue() as {
      records: { child_id: string; status: string; note: string }[];
      visitors: { name: string; status: string; note: string }[];
    };
    const records = raw.records
      .filter((record) => record.status !== '')
      .map((record) => ({
        child_id: record.child_id,
        status: record.status as AttendanceStatus,
        note: record.note.trim() || null,
      }));
    const visitors = raw.visitors
      .filter((visitor) => visitor.name.trim() !== '')
      .map((visitor) => ({
        name: visitor.name.trim(),
        status: (visitor.status || 'present') as AttendanceStatus,
        note: visitor.note.trim() || null,
      }));
    try {
      const data = await firstValueFrom(
        this.api.put<SessionAttendance>(`/class-sessions/${session.id}/attendance`, {
          records,
          visitors,
        }),
      );
      this.applyAttendance(data);
      this.message.set('Attendance saved.');
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  addVisitor(): void {
    this.visitorRecords.push(
      this.fb.group({
        name: [''],
        status: ['present'],
        note: [''],
      }),
    );
  }

  removeVisitor(index: number): void {
    this.visitorRecords.removeAt(index);
  }

  toggleVolunteer(volunteerId: string, checked: boolean): void {
    const current = new Set(this.selectedVolunteerIds());
    if (checked) {
      current.add(volunteerId);
    } else {
      current.delete(volunteerId);
    }
    this.selectedVolunteerIds.set([...current]);
  }

  isVolunteerSelected(volunteerId: string): boolean {
    return this.selectedVolunteerIds().includes(volunteerId);
  }

  async saveVolunteers(): Promise<void> {
    const session = this.selectedSession();
    if (!session) {
      return;
    }
    this.volunteersSaving.set(true);
    this.error.set(null);
    this.message.set(null);
    try {
      const data = await firstValueFrom(
        this.api.put<{ volunteers: SessionVolunteer[] }>(
          `/class-sessions/${session.id}/volunteers`,
          { volunteer_ids: this.selectedVolunteerIds() },
        ),
      );
      this.sessionVolunteers.set(data.volunteers);
      this.message.set('Session volunteers saved.');
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.volunteersSaving.set(false);
    }
  }

  async loadReport(): Promise<void> {
    const classId = this.filters.controls.class_id.value;
    if (!classId || this.reportForm.invalid) {
      this.reportForm.markAllAsTouched();
      return;
    }
    this.error.set(null);
    try {
      const value = this.reportForm.getRawValue();
      const report = await firstValueFrom(
        this.api.get<AttendanceReport>('/reports/attendance', {
          from: value.from,
          to: value.to,
          class_id: classId,
        }),
      );
      this.report.set(report);
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  async downloadCsv(): Promise<void> {
    const classId = this.filters.controls.class_id.value;
    if (!classId || this.reportForm.invalid) {
      this.reportForm.markAllAsTouched();
      return;
    }
    this.error.set(null);
    const value = this.reportForm.getRawValue();
    try {
      const blob = await firstValueFrom(
        this.api.getBlob('/reports/attendance.csv', {
          from: value.from,
          to: value.to,
          class_id: classId,
        }),
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `attendance-${value.from}-${value.to}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  percent(rate: number | null): string {
    return rate === null ? '—' : `${Math.round(rate * 100)}%`;
  }

  className(): string {
    const id = this.filters.controls.class_id.value;
    return this.classes().find((item) => item.id === id)?.name ?? 'class';
  }

  private applyAttendance(data: SessionAttendance): void {
    this.attendance.set(data);
    this.attendanceRecords.clear();
    for (const entry of data.entries) {
      this.attendanceRecords.push(
        this.fb.group({
          child_id: [entry.child.id],
          status: [entry.status ?? ''],
          note: [entry.note ?? ''],
        }),
      );
    }
    this.visitorRecords.clear();
    for (const visitor of data.visitors) {
      this.visitorRecords.push(
        this.fb.group({
          name: [visitor.visitor_name],
          status: [visitor.status],
          note: [visitor.note ?? ''],
        }),
      );
    }
  }

  private resourceGroup(label = '', url = ''): FormGroup {
    return this.fb.group({ label: [label], url: [url] });
  }
}
