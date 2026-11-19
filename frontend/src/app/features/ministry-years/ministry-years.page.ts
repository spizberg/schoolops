import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { ApiService, errorMessage } from '../../core/api';
import { MinistryYear, NoClassDay, NoClassDayKind, Page } from '../../core/models';

const WEEKDAY_NAMES: Record<number, string> = {
  1: 'Mon',
  2: 'Tue',
  3: 'Wed',
  4: 'Thu',
  5: 'Fri',
  6: 'Sat',
  7: 'Sun',
};

@Component({
  selector: 'app-ministry-years-page',
  imports: [ReactiveFormsModule],
  templateUrl: './ministry-years.page.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MinistryYearsPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);

  readonly years = signal<MinistryYear[]>([]);
  readonly selected = signal<MinistryYear | null>(null);
  readonly noClassDays = signal<NoClassDay[]>([]);
  readonly meetingDays = signal<string[]>([]);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  readonly yearForm = this.fb.nonNullable.group({
    label: ['', [Validators.required, Validators.maxLength(50)]],
    start_date: ['', Validators.required],
    end_date: ['', Validators.required],
    is_active: false,
  });

  readonly dayForm = this.fb.nonNullable.group({
    date: ['', Validators.required],
    name: ['', [Validators.required, Validators.maxLength(120)]],
    kind: ['closure' as NoClassDayKind, Validators.required],
  });

  readonly rangeForm = this.fb.nonNullable.group({
    from: ['', Validators.required],
    to: ['', Validators.required],
  });

  ngOnInit(): void {
    void this.loadYears();
  }

  async loadYears(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const page = await firstValueFrom(this.api.get<Page<MinistryYear>>('/ministry-years'));
      this.years.set(page.items);
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }

  async createYear(): Promise<void> {
    if (this.yearForm.invalid) {
      this.yearForm.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    try {
      await firstValueFrom(
        this.api.post<MinistryYear>('/ministry-years', this.yearForm.getRawValue()),
      );
      this.yearForm.reset({ label: '', start_date: '', end_date: '', is_active: false });
      await this.loadYears();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  async activate(year: MinistryYear): Promise<void> {
    this.error.set(null);
    try {
      await firstValueFrom(
        this.api.post<MinistryYear>(`/ministry-years/${year.id}/activate`, {}),
      );
      await this.loadYears();
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  async selectYear(year: MinistryYear): Promise<void> {
    this.selected.set(year);
    this.error.set(null);
    this.rangeForm.setValue({ from: year.start_date, to: year.end_date });
    await Promise.all([this.loadNoClassDays(), this.loadMeetingDays()]);
  }

  async loadNoClassDays(): Promise<void> {
    const year = this.selected();
    if (!year) {
      return;
    }
    try {
      const days = await firstValueFrom(
        this.api.get<NoClassDay[]>(`/ministry-years/${year.id}/no-class-days`),
      );
      this.noClassDays.set(days);
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  async addNoClassDay(): Promise<void> {
    const year = this.selected();
    if (!year || this.dayForm.invalid) {
      this.dayForm.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    try {
      await firstValueFrom(
        this.api.post<NoClassDay>(
          `/ministry-years/${year.id}/no-class-days`,
          this.dayForm.getRawValue(),
        ),
      );
      this.dayForm.reset({ date: '', name: '', kind: 'closure' });
      await Promise.all([this.loadNoClassDays(), this.loadMeetingDays()]);
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  async deleteNoClassDay(day: NoClassDay): Promise<void> {
    if (!globalThis.confirm(`Remove "${day.name}" from the calendar?`)) {
      return;
    }
    try {
      await firstValueFrom(this.api.delete(`/no-class-days/${day.id}`));
      await Promise.all([this.loadNoClassDays(), this.loadMeetingDays()]);
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  async loadMeetingDays(): Promise<void> {
    const year = this.selected();
    if (!year || this.rangeForm.invalid) {
      return;
    }
    try {
      const result = await firstValueFrom(
        this.api.get<{ items: string[] }>(`/ministry-years/${year.id}/meeting-days`, {
          from: this.rangeForm.controls.from.value,
          to: this.rangeForm.controls.to.value,
        }),
      );
      this.meetingDays.set(result.items);
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  weekdays(days: number[]): string {
    return days.map((day) => WEEKDAY_NAMES[day] ?? String(day)).join(', ');
  }
}
