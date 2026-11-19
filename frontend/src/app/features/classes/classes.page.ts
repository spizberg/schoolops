import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { ApiService, errorMessage } from '../../core/api';
import {
  Child,
  ClassGroup,
  Enrollment,
  MinistryYear,
  Page,
  RosterEntry,
  Volunteer,
} from '../../core/models';

@Component({
  selector: 'app-classes-page',
  imports: [ReactiveFormsModule],
  templateUrl: './classes.page.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClassesPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);

  readonly today = new Date().toISOString().slice(0, 10);

  readonly years = signal<MinistryYear[]>([]);
  readonly volunteers = signal<Volunteer[]>([]);
  readonly children = signal<Child[]>([]);
  readonly classes = signal<ClassGroup[]>([]);
  readonly selected = signal<ClassGroup | null>(null);
  readonly roster = signal<RosterEntry[]>([]);
  readonly loading = signal(false);
  readonly rosterLoading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  readonly filters = this.fb.nonNullable.group({
    ministry_year_id: [''],
  });

  readonly form = this.fb.group({
    name: this.fb.nonNullable.control('', [
      Validators.required,
      Validators.maxLength(100),
    ]),
    ministry_year_id: this.fb.nonNullable.control('', Validators.required),
    age_band: this.fb.nonNullable.control('', [
      Validators.required,
      Validators.maxLength(50),
    ]),
    age_min: this.fb.control<number | null>(null),
    age_max: this.fb.control<number | null>(null),
    lead_volunteer_id: this.fb.nonNullable.control(''),
    room: this.fb.nonNullable.control(''),
    capacity: this.fb.control<number | null>(null),
    curriculum: this.fb.nonNullable.control(''),
  });

  readonly enrollForm = this.fb.nonNullable.group({
    child_id: ['', Validators.required],
    start_date: [this.today, Validators.required],
    end_date: [''],
  });

  ngOnInit(): void {
    void this.bootstrap();
  }

  async bootstrap(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const [years, volunteers, children] = await Promise.all([
        firstValueFrom(this.api.get<Page<MinistryYear>>('/ministry-years', { limit: 100 })),
        firstValueFrom(
          this.api.get<Page<Volunteer>>('/volunteers', { status: 'active', limit: 100 }),
        ),
        firstValueFrom(
          this.api.get<Page<Child>>('/children', { status: 'active', limit: 100 }),
        ),
      ]);
      this.years.set(years.items);
      this.volunteers.set(volunteers.items);
      this.children.set(children.items);
      await this.loadClasses();
    } catch (error) {
      this.error.set(errorMessage(error));
      this.loading.set(false);
    }
  }

  async loadClasses(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    this.selected.set(null);
    this.roster.set([]);
    try {
      const page = await firstValueFrom(
        this.api.get<Page<ClassGroup>>('/classes', {
          ministry_year_id: this.filters.controls.ministry_year_id.value,
          limit: 100,
        }),
      );
      this.classes.set(page.items);
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }

  async createClass(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    const value = this.form.getRawValue();
    const payload = {
      name: value.name,
      ministry_year_id: value.ministry_year_id,
      age_band: value.age_band,
      age_min: value.age_min,
      age_max: value.age_max,
      lead_volunteer_id: value.lead_volunteer_id || null,
      room: value.room.trim() || null,
      capacity: value.capacity,
      curriculum: value.curriculum.trim() || null,
    };
    try {
      await firstValueFrom(this.api.post<ClassGroup>('/classes', payload));
      this.form.reset({
        name: '',
        ministry_year_id: value.ministry_year_id,
        age_band: '',
        age_min: null,
        age_max: null,
        lead_volunteer_id: '',
        room: '',
        capacity: null,
        curriculum: '',
      });
      await this.loadClasses();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  async selectClass(schoolClass: ClassGroup): Promise<void> {
    this.selected.set(schoolClass);
    this.enrollForm.reset({ child_id: '', start_date: this.today, end_date: '' });
    await this.loadRoster();
  }

  async loadRoster(): Promise<void> {
    const schoolClass = this.selected();
    if (!schoolClass) {
      return;
    }
    this.rosterLoading.set(true);
    this.error.set(null);
    try {
      const page = await firstValueFrom(
        this.api.get<Page<RosterEntry>>(`/classes/${schoolClass.id}/enrollments`, {
          on_date: this.today,
          limit: 100,
        }),
      );
      this.roster.set(page.items);
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.rosterLoading.set(false);
    }
  }

  async enroll(): Promise<void> {
    const schoolClass = this.selected();
    if (!schoolClass || this.enrollForm.invalid) {
      this.enrollForm.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    const value = this.enrollForm.getRawValue();
    try {
      await firstValueFrom(
        this.api.post<Enrollment>(`/classes/${schoolClass.id}/enrollments`, {
          child_id: value.child_id,
          start_date: value.start_date,
          end_date: value.end_date || null,
        }),
      );
      this.enrollForm.reset({ child_id: '', start_date: this.today, end_date: '' });
      await this.loadRoster();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  async endEnrollment(entry: RosterEntry): Promise<void> {
    if (
      !globalThis.confirm(
        `End ${entry.child.first_name} ${entry.child.last_name}'s enrollment?`,
      )
    ) {
      return;
    }
    this.error.set(null);
    try {
      await firstValueFrom(this.api.delete(`/enrollments/${entry.id}`));
      await this.loadRoster();
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  async deleteClass(schoolClass: ClassGroup): Promise<void> {
    if (!globalThis.confirm(`Delete class ${schoolClass.name}?`)) {
      return;
    }
    this.error.set(null);
    try {
      await firstValueFrom(this.api.delete(`/classes/${schoolClass.id}`));
      if (this.selected()?.id === schoolClass.id) {
        this.selected.set(null);
        this.roster.set([]);
      }
      await this.loadClasses();
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  yearLabel(id: string): string {
    return this.years().find((year) => year.id === id)?.label ?? '—';
  }

  volunteerName(id: string | null): string {
    if (!id) {
      return '—';
    }
    const volunteer = this.volunteers().find((item) => item.id === id);
    return volunteer ? `${volunteer.first_name} ${volunteer.last_name}` : '—';
  }
}
