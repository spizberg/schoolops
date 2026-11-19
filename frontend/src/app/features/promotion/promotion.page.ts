import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { ApiService, errorMessage } from '../../core/api';
import {
  ClassGroup,
  ClassMapping,
  MinistryYear,
  Page,
  PromotionApplyResult,
  PromotionPreview,
} from '../../core/models';

@Component({
  selector: 'app-promotion-page',
  imports: [ReactiveFormsModule],
  templateUrl: './promotion.page.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PromotionPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);

  readonly years = signal<MinistryYear[]>([]);
  readonly sourceClasses = signal<ClassGroup[]>([]);
  readonly targetClasses = signal<ClassGroup[]>([]);
  readonly preview = signal<PromotionPreview | null>(null);
  readonly result = signal<PromotionApplyResult | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  readonly yearForm = this.fb.nonNullable.group({
    source_year_id: ['', Validators.required],
    target_year_id: ['', Validators.required],
  });

  readonly mappingForm = this.fb.group({
    mappings: this.fb.array([]),
  });

  get mappings(): FormArray {
    return this.mappingForm.controls.mappings;
  }

  ngOnInit(): void {
    void this.loadYears();
  }

  async loadYears(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const page = await firstValueFrom(
        this.api.get<Page<MinistryYear>>('/ministry-years', { limit: 100 }),
      );
      this.years.set(page.items);
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }

  async loadClasses(): Promise<void> {
    if (this.yearForm.invalid) {
      this.yearForm.markAllAsTouched();
      return;
    }
    const { source_year_id, target_year_id } = this.yearForm.getRawValue();
    if (source_year_id === target_year_id) {
      this.error.set('Source and target years must differ.');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.preview.set(null);
    this.result.set(null);
    try {
      const [source, target] = await Promise.all([
        firstValueFrom(
          this.api.get<Page<ClassGroup>>('/classes', {
            ministry_year_id: source_year_id,
            limit: 100,
          }),
        ),
        firstValueFrom(
          this.api.get<Page<ClassGroup>>('/classes', {
            ministry_year_id: target_year_id,
            limit: 100,
          }),
        ),
      ]);
      this.sourceClasses.set(source.items);
      this.targetClasses.set(target.items);
      this.mappings.clear();
      for (const schoolClass of source.items) {
        this.mappings.push(
          this.fb.group({
            source_class_id: [schoolClass.id],
            source_name: [schoolClass.name],
            target_class_id: [''],
          }),
        );
      }
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }

  async previewPromotion(): Promise<void> {
    const payload = this.payload();
    if (!payload) {
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    try {
      const preview = await firstValueFrom(
        this.api.post<PromotionPreview>('/promotions/preview', payload),
      );
      this.preview.set(preview);
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  async applyPromotion(): Promise<void> {
    const payload = this.payload();
    if (!payload) {
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    try {
      const result = await firstValueFrom(
        this.api.post<PromotionApplyResult>('/promotions/apply', payload),
      );
      this.result.set(result);
      await this.previewPromotion();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  private payload(): {
    source_year_id: string;
    target_year_id: string;
    mappings: ClassMapping[];
  } | null {
    if (this.yearForm.invalid) {
      this.yearForm.markAllAsTouched();
      return null;
    }
    const raw = this.mappingForm.getRawValue() as {
      mappings: { source_class_id: string; target_class_id: string }[];
    };
    const mappings: ClassMapping[] = raw.mappings
      .filter((mapping) => mapping.target_class_id !== '')
      .map((mapping) => ({
        source_class_id: mapping.source_class_id,
        target_class_id: mapping.target_class_id,
      }));
    if (mappings.length === 0) {
      this.error.set('Map at least one source class to a target class.');
      return null;
    }
    const value = this.yearForm.getRawValue();
    return {
      source_year_id: value.source_year_id,
      target_year_id: value.target_year_id,
      mappings,
    };
  }
}
