import { SetMetadata } from '@nestjs/common';

export const IS_PUBLIC_KEY = 'isPublic';

/** يجعل الـ endpoint عاماً (لا يتطلب مصادقة). */
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);
