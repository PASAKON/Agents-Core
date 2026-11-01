# บทซีรีส์ยาว ตอนที่ 1: "เสียงเตือนจากมือถือ" (DAY 0)
ความยาว: ประมาณ 10–12 นาที (สัดส่วน 16:9)

| # | scene | still | line | game |
|---|---|---|---|---|
| 1 | 1 | L1-S01 | เรื่องสมมติ อิงเหตุการณ์จริง คำแนะนำเอาชีวิตรอดทั้งหมดอิงข้อมูลจริงที่มีแหล่งชัดเจน มาเริ่มวันแรกไปด้วยกันนะคะ | `world disclaimer` |
| 2 | 1 | L1-S01 | ตีสามตรง กลางดึกที่เงียบสนิท อยู่ดีๆ มือถือของข้าวหอมก็ส่งเสียงเตือนภัยแหลมสูงดังลั่นห้องจนสะดุ้งตื่น | `world alert_sound / mind -5` |
| 3 | 1 | L1-S01 | เสียงเตือนหวีดแหลมรัวเร็ว หน้าจอสว่างวาบเป็นข้อความเตือนภัยฉุกเฉินระดับชาติที่ส่งตรงเข้ามือถือพร้อมกัน | `world alert_cell_broadcast` |
| 4 | 1 | L1-S02 | ข้าวหอมงัวเงียลุกขึ้นมานั่งบนเตียง มือรีบคว้าโทรศัพท์ขึ้นมาดูด้วยใจเต้นรัว ว่าเกิดเรื่องด่วนอะไรขึ้น | `pass hours=0.1 / mind -5` |
| 5 | 1 | L1-S02 | ตามข้อมูลกรมป้องกันและบรรเทาสาธารณภัย การเตือนภัยฉุกเฉินผ่านมือถือจะแจ้งหน่วยงาน ภัยพิบัติ เวลา และสายด่วนหนึ่งเจ็ดแปดสี่ | `xp read_alert Lv1` |
| 6 | 1 | L1-S02 | บนหน้าจอระบุชัดเจนจากกรมป้องกันและบรรเทาสาธารณภัย เตือนภัยฝนตกหนักและน้ำท่วมฉับพลัน เวลาตีสาม ให้เฝ้าระวังสูงสุด | `world alert_ddpm` |
| 7 | 1 | L1-S03 | ข้าวหอมกะพริบตาถี่ๆ รีบลุกจากเตียงแล้วเดินตรงไปแง้มผ้าม่านหน้าต่างห้องนอน เพื่อมองดูบรรยากาศข้างนอก | `pass hours=0.1` |
| 8 | 1 | L1-S03 | ข้างนอกฝนกำลังเทกระหน่ำลงมาอย่างหนัก ลมพัดแรงจนต้นไม้หน้าบ้านเอนไหว เม็ดฝนซัดหน้าต่างจนแทบมองไม่เห็นทาง | `world heavy_rain` |
| 9 | 1 | L1-S03 | ข้าวหอมเพ่งสายตาฝ่าความมืดลงไปมองที่ถนนคอนกรีตหน้าบ้าน ด้วยความรู้สึกสังหรณ์ใจว่าครั้งนี้ไม่ธรรมดา | `mind -5` |
| 10 | 1 | L1-S04 | พอมองลงไปก็เห็นน้ำสีขุ่นเอ่อล้นขึ้นมาจากท่อระบายน้ำ ไหลบ่าเข้าท่วมพื้นถนนในซอยจนกลายเป็นผืนน้ำ | `world water_rising` |
| 11 | 1 | L1-S04 | ระดับน้ำในซอยตอนนี้ท่วมสูงประมาณข้อเท้า หรือราวสิบเซนติเมตร และกระแสน้ำยังคงไหลเชี่ยวเพิ่มขึ้นเรื่อยๆ | `world water_depth_ankle` |
| 12 | 1 | L1-S04 | บรรยากาศรอบข้างมืดสนิท มีเพียงแสงไฟส้มสลัวจากเสาไฟ สะท้อนผิวน้ำที่กำลังไหลวนอยู่อย่างน่าหวาดระแวง | `pass hours=0.1` |
| 13 | 1 | L1-S05 | ข้าวหอมก้มดูมือถือ แบตเตอรี่ยังเต็มร้อยเปอร์เซ็นต์ และมีเงินสดติดตัวอยู่ในห้องตอนนี้รวมแล้วสามพันบาท | `money 3000 / battery 100%` |
| 14 | 1 | L1-S05 | การแจ้งเตือนตอนตีสามไม่ใช่เรื่องล้อเล่นแน่ๆ ข้าวหอมบอกตัวเองว่า ถ้ามัวแต่นอนต่อ ตอนเช้าคงหนีไม่ทันแล้ว | `mind +5` |
| 15 | 1 | L1-S05 | ดึงสติกลับมา วันศูนย์เริ่มต้นขึ้นแล้ว คุณพร้อมที่จะเอาชีวิตรอดไปด้วยกันกับข้าวหอมหรือยังคะ | `mind +5` |
| 16 | 2 | L1-S06 | ข้าวหอมเปิดโทรศัพท์มือถือเข้าแอปข่าวทันที เพื่อเช็กประกาศเพิ่มเติมจากหน่วยงานราชการว่าเกิดอะไรขึ้น | `pass hours=0.2 / use phone` |
| 17 | 2 | L1-S06 | ข่าวรายงานว่ามีมวลน้ำขนาดใหญ่กำลังหลากลงมาจากทางเหนือ และฝนตกสะสมทำให้ระดับน้ำตามคูคลองล้นตลิ่ง | `world flood_forecast` |
| 18 | 2 | L1-S06 | ทางการเตือนให้ชุมชนที่ลุ่มต่ำเตรียมรับมือน้ำท่วมฉับพลัน ข้าวหอมรู้ทันทีว่าสถานการณ์รอบนี้หนักแน่ | `xp assess_news Lv1` |
| 19 | 2 | L1-S07 | ข้าวหอมรีบเดินลงมาชั้นล่าง แง้มประตูรั้วหน้าบ้านออกไปสำรวจระดับน้ำจริงในซอยให้เห็นชัดๆ กับตา | `pass hours=0.2` |
| 20 | 2 | L1-S07 | ข้าวหอมนำไม้บรรทัดยาวจุ่มวัดระดับน้ำหน้าบ้าน น้ำท่วมสูงปริ่มตาตุ่ม วัดได้ประมาณสิบเซนติเมตรพอดี | `loot measure_stick n=1 / use measure_stick` |
| 21 | 2 | L1-S07 | อย่าคิดว่าน้ำสิบเซนติเมตรไม่อันตรายนะคะ ตามข้อมูลหน่วยงานอุตุนิยมวิทยาแห่งชาติสหรัฐ น้ำไหลแรงสูงแค่สิบห้าเซนติเมตรก็ซัดคนล้มได้แล้ว | `xp nws_water_danger Lv1` |
| 22 | 2 | L1-S07 | และตามข้อมูลกรมอนามัย น้ำสูงเพียงสิบห้าเซนติเมตรก็ทำให้ยานพาหนะเสียหลักได้ จึงห้ามเดินฝ่าน้ำไหลเด็ดขาด | `xp vehicle_water_danger Lv1` |
| 23 | 2 | L1-S08 | ข้าวหอมมองไปตามซอย บ้านทุกหลังยังคงปิดไฟมืดสนิท หน้าต่างและประตูยังปิดล็อกแน่นหนาเหมือนเดิม | `world neighbours_asleep` |
| 24 | 2 | L1-S08 | เพื่อนบ้านส่วนใหญ่ยังหลับสบายอยู่บนเตียง ไม่มีใครรู้เลยว่าสายน้ำเย็นเฉียบกำลังไหลมาประชิดบันไดบ้านแล้ว | `mind -2` |
| 25 | 2 | L1-S08 | ทุกคนคงคิดว่าเป็นแค่น้ำรอระบายเหมือนเคย แต่การเตือนภัยระดับนี้ ข้าวหอมรู้ดีว่านี่ไม่ใช่น้ำท่วมธรรมดา | `mind +2` |
| 26 | 2 | L1-S09 | ข้าวหอมเดินกลับเข้าบ้าน เปิดลิ้นชักหยิบเงินสดสำรองออกมานับ มีธนบัตรใบละพันและร้อยรวมได้สามพันบาทพอดี | `loot cash n=3000` |
| 27 | 2 | L1-S09 | ตามข้อมูลเหตุการณ์เฮอริเคนมาเรีย เมื่อไฟดับ บัตรเครดิตและตู้เอทีเอ็มจะใช้ไม่ได้ ต้องพึ่งเงินสดเท่านั้น | `xp cash_necessity Lv1` |
| 28 | 2 | L1-S09 | เงินสดสามพันบาทนี้คือทุนก้อนเดียว ข้าวหอมต้องรีบออกไปซื้อเสบียงก่อนที่ร้านค้าจะปิดหรือของจะหมดเกลี้ยง | `mind +5` |
| 29 | 3 | L1-S10 | ข้าวหอมหยิบเสื้อกันฝนสีเหลืองตัวเก่งมาสวม รูดซิปติดกระดุม สวมหมวกคลุมมิดชิดเพื่อกันฝนและลมหนาว | `use yellow_raincoat` |
| 30 | 3 | L1-S10 | ก้าวเท้าลุยน้ำออกจากบ้าน น้ำเย็นเฉียบท่วมข้อเท้า ข้าวหอมเดินฝ่าความมืดตรงไปยังร้านสะดวกซื้อปากซอย | `pass hours=0.3 / water -2` |
| 31 | 3 | L1-S11 | พอถึงปากซอย ข้าวหอมก็ตกใจ เมื่อเห็นคนยืนต่อคิวยาวเหยียดทะลักออกมานอกชายคาร้านสะดวกซื้อ | `world store_queue` |
| 32 | 3 | L1-S11 | ตามข้อมูลเหตุการณ์น้ำท่วมใหญ่ปีสองห้าห้าสี่ ประชาชนจะเริ่มกักตุนอาหารแห้งและน้ำดื่มตั้งแต่ก่อนที่น้ำจะมาถึงเสมอ | `xp flood_history_2554 Lv1` |
| 33 | 3 | L1-S11 | คนในแถวใส่ชุดนอน กางร่ม ยืนหนาวสั่นรอกันเงียบๆ บรรยากาศเต็มไปด้วยความตึงเครียดและความกังวลใจ | `pass hours=0.5 / mind -3` |
| 34 | 3 | L1-S12 | ข้าวหอมต่อคิวจนได้เข้ามาในร้าน แต่สภาพบนชั้นวางของทำเอาใจหาย เพราะสินค้าจำเป็นถูกกวาดไปเกือบหมด | `world store_shelves_empty` |
| 35 | 3 | L1-S12 | บะหมี่กึ่งสำเร็จรูปหมดเกลี้ยง เช่นเดียวกับข้อมูลปีสองห้าห้าสี่ ที่ของจะขาดตลาดและไข่ไก่จะราคาพุ่งขึ้นหลายเท่า | `world food_shortage` |
| 36 | 3 | L1-S12 | ข้าวหอมรีบเดินไปแผนกเครื่องดื่ม แต่น้ำดื่มบรรจุขวดแพ็กใหญ่เหลือวางอยู่เพียงไม่กี่แพ็กสุดท้ายบนชั้น | `world water_running_low` |
| 37 | 3 | L1-S13 | จังหวะนั้น ชายร่างท้วมคนหนึ่งก็เข็นรถเข็นแทรกเข้ามา แล้วกวาดน้ำดื่มทั้งชั้นลงรถเข็นตัวเองจนหมดเกลี้ยง | `world selfish_hoarder` |
| 38 | 3 | L1-S13 | เขายืนยิ้มแป้นอย่างภูมิใจที่มีน้ำเต็มคันรถ โดยไม่สนใจสายตาของคนข้างหลังที่ยืนรออยู่เลยแม้แต่น้อย | `mind -5` |
| 39 | 3 | L1-S14 | ข้าวหอมกับป้าข้างๆ ได้แต่มองหน้ากันตาปริบๆ ข้าวหอมแอบมองค้อนแล้วอมยิ้มขำๆ ไม่ได้มีเรื่องทะเลาะกันนะคะ | `mind +2` |
| 40 | 3 | L1-S14 | โชคดีที่พนักงานเข็นน้ำดื่มขนาดกลางออกมาเติมพอดี ข้าวหอมจึงรีบหยิบมาได้สองแพ็กอย่างเฉียดฉิว | `loot water_pack n=2` |
| 41 | 3 | L1-S15 | ตอนนี้ข้าวหอมมีงบอยู่สามพันบาท ถ้าเป็นคุณตกอยู่ในสถานการณ์นี้ คุณจะเลือกซื้ออะไรสามอย่างคะ | `world choice_card_start` |
| 42 | 3 | L1-S15 | การ์ดทางเลือกให้คิดดูนะคะ ข้อหนึ่ง น้ำดื่ม อาหารแห้ง ถ่านไฟฉาย หรือข้อสอง ขนมขบเคี้ยว น้ำอัดลม เทียนไข | `world choice_card_options` |
| 43 | 3 | L1-S15 | ลองพิมพ์คอมเมนต์บอกข้าวหอมใต้คลิปนี้นะคะ ข้าวหอมให้เวลาคิดสามวินาที ก่อนจะไปดูของที่ข้าวหอมเลือกกันค่ะ | `pass hours=0.1` |
| 44 | 3 | L1-S16 | เฉลยคือข้อหนึ่งค่ะ ข้าวหอมเลือกน้ำดื่มสะอาด อาหารแห้งพร้อมทาน และถ่านไฟฉายสำหรับเป็นพลังงานสำรอง | `xp item_choice Lv1` |
| 45 | 3 | L1-S16 | ตามข้อมูลศูนย์ควบคุมโรคสหรัฐ เมื่อไฟดับให้ใช้ไฟฉายแทนเทียนไขเพื่อเลี่ยงไฟไหม้ ข้าวหอมเลยหยิบถ่านไฟฉายมาสองแพ็ก | `loot battery_pack n=2` |
| 46 | 3 | L1-S16 | และหยิบปลากระป๋องกับขนมปังกรอบที่เปิดกินได้เลยโดยไม่ต้องต้ม เพราะยามวิกฤติเราอาจไม่มีไฟสำหรับหุงต้ม | `loot canned_fish n=4 / loot biscuits n=2` |
| 47 | 3 | L1-S17 | ข้าวหอมจ่ายเงินสดไปแปดร้อยห้าสิบบาท ซึ่งเป็นราคาสมมตินะคะ ทำให้ตอนนี้เหลือเงินสดสองพันหนึ่งร้อยห้าสิบบาท | `money -850 (ราคาสมมติ) / pass hours=0.4` |
| 48 | 4 | L1-S18 | ข้าวหอมหอบหิ้วเสบียงเดินลุยน้ำกลับถึงบ้านอย่างปลอดภัย ตอนนี้หกโมงเช้า ท้องฟ้าเริ่มสว่างขึ้นทีละน้อย | `pass hours=1 / water -3` |
| 49 | 4 | L1-S18 | วางของเสร็จ ข้าวหอมรีบลงมือเตรียมบ้านรับมือน้ำท่วมทันที เพราะน้ำนอกบ้านกำลังสูงขึ้นเรื่อยๆ ทุกนาที | `mind +5` |
| 50 | 4 | L1-S19 | ภารกิจแรกคือยกของมีค่า เครื่องใช้ไฟฟ้า ปลั๊กพ่วง และไมโครเวฟ ขึ้นวางบนชั้นสูงให้พ้นระดับน้ำท่วม | `use lift_appliances / pass hours=0.5` |
| 51 | 4 | L1-S19 | ตามข้อมูลกรมอนามัย ให้ปิดเครื่องใช้ไฟฟ้า เตาแก๊ส และเตรียมยกเบรกเกอร์ให้เรียบร้อยเพื่อความปลอดภัย | `xp dohm_home_prep Lv1` |
| 52 | 4 | L1-S20 | เรื่องไฟฟ้าอันตรายถึงชีวิต ตามข้อมูลการไฟฟ้านครหลวง หากรู้แน่ชัดว่าน้ำกำลังจะท่วมเข้าบ้าน ให้เตรียมปลดเมนเบรกเกอร์ | `xp mea_breaker_rule Lv1` |
| 53 | 4 | L1-S20 | และการไฟฟ้านครหลวงย้ำว่า ห้ามแตะสวิตช์ไฟ และงดใช้ไฟฟ้าขณะตัวเปียกหรือยืนในน้ำเด็ดขาด เพราะอาจถูกไฟดูดได้ | `xp mea_wet_electric Lv1` |
| 54 | 4 | L1-S20 | ข้าวหอมเขียนป้ายระบุสวิตช์เบรกเกอร์แต่ละจุดตามคำแนะนำกรมอนามัย เพื่อให้รู้ว่าตัวไหนคุมไฟชั้นล่างและชั้นบน | `use label_breakers` |
| 55 | 4 | L1-S21 | และถ้าพบคนถูกไฟดูดช่วงน้ำท่วม ตามข้อมูลกรมอนามัย ห้ามพุ่งตัวเข้าไปช่วยด้วยมือเปล่าหรือลุยน้ำเข้าไปเด็ดขาด | `xp shock_warning Lv1` |
| 56 | 4 | L1-S21 | ตามข้อมูลกรมอนามัยและการไฟฟ้าส่วนภูมิภาค ให้ตัดเบรกเกอร์ก่อน แล้วใช้วัสดุฉนวนแห้ง เช่น ไม้แห้ง พลาสติกแห้ง หรือผ้าแห้ง แยกผู้ป่วยออกมา | `xp shock_separation Lv1` |
| 57 | 4 | L1-S21 | โทรหนึ่งหกหกเก้า หากหยุดหายใจให้ทำซีพีอาร์ทันที กดหน้าอกลึกห้าถึงหกเซนติเมตร และต้องส่งโรงพยาบาลทุกราย | `xp cpr_guideline Lv1` |
| 58 | 4 | L1-S22 | เรื่องน้ำดื่มน้ำใช้ ตามข้อมูลหน่วยงานจัดการเหตุฉุกเฉินสหรัฐ ต้องสำรองน้ำอย่างน้อยคนละหนึ่งแกลลอน หรือประมาณสามจุดแปดลิตรต่อวัน | `xp fema_water_quota Lv1` |
| 59 | 4 | L1-S22 | ข้าวหอมนำหม้อใบใหญ่ กะละมัง ถังน้ำ และขวดเปล่าในครัวทั้งหมด มาล้างทำความสะอาดเพื่อเตรียมกักตุนน้ำประปา | `pass hours=0.5 / use clean_containers` |
| 60 | 4 | L1-S23 | ตามข้อมูลกรมอนามัย ให้เปิดน้ำประปารองใส่ภาชนะที่มีฝาปิดมิดชิด ข้าวหอมเปิดน้ำกรอกใส่ทุกภาชนะจนเต็มแล้วปิดฝาแน่นหนา | `water +30` |
| 61 | 4 | L1-S23 | เพราะถ้าน้ำท่วม ระบบประปาอาจจะปนเปื้อนหรือหยุดไหล การสำรองน้ำไว้ตั้งแต่ตอนที่น้ำยังใสจึงเป็นเรื่องสำคัญที่สุด | `loot clean_water_reserve n=6` |
| 62 | 4 | L1-S24 | ต่อมาคือการเตรียมถุงยังชีพฉุกเฉินสำหรับอพยพ ตามคำแนะนำของหน่วยงานจัดการเหตุฉุกเฉินสหรัฐและกรมอนามัย | `use prep_go_bag` |
| 63 | 4 | L1-S24 | ข้าวหอมนำเป้กันน้ำมาใส่ขวดน้ำ อาหารแห้ง ไฟฉายพร้อมถ่านสำรอง วิทยุพกพา และชุดปฐมพยาบาลพร้อมยาประจำตัว | `loot firstaid_kit n=1 / loot torch n=1 / loot radio n=1` |
| 64 | 4 | L1-S24 | และสิ่งที่ขาดไม่ได้คือนกหวีดค่ะ นกหวีดมีประโยชน์อย่างยิ่งในการเป่าส่งสัญญาณขอความช่วยเหลือโดยไม่ต้องเปลืองแรง | `loot whistle n=1` |
| 65 | 4 | L1-S25 | สำหรับเอกสารสำคัญ ตามข้อมูลหน่วยงานจัดการเหตุฉุกเฉินสหรัฐ ต้องจัดเก็บเอกสารสำคัญไว้ในภาชนะกันน้ำที่พกพาสะดวก | `xp doc_waterproof Lv1` |
| 66 | 4 | L1-S25 | ข้าวหอมรวบรวมบัตรประชาชน ทะเบียนบ้าน และเงินสดที่เหลือ ใส่ลงในถุงพลาสติกกันน้ำ ปิดผนึกแน่นหนาแล้วเก็บใส่เป้ | `use pack_documents` |
| 67 | 4 | L1-S26 | สุดท้ายคือเรื่องพลังงาน ข้าวหอมนำโทรศัพท์มือถือและแบตเตอรี่สำรองทุกก้อนที่มี มาเสียบชาร์จจนเต็มร้อยเปอร์เซ็นต์ | `battery 100% / loot powerbank n=2` |
| 68 | 4 | L1-S26 | ชาร์จไฟฉายให้เต็ม และตรวจเช็กวิทยุแบบใส่ถ่านให้พร้อมรับฟังข่าวสารยามที่ระบบอินเทอร์เน็ตหรือสัญญาณมือถือใช้ไม่ได้ | `xp energy_management Lv1` |
| 69 | 4 | L1-S26 | ถึงช่วงเที่ยงวัน ทั้งตัวบ้านและถุงยังชีพของข้าวหอมพร้อมรับมือแล้ว สภาพจิตใจตอนนี้รู้สึกมั่นใจขึ้นมากเลยค่ะ | `mind +10 / pass hours=2` |
| 70 | 5 | L1-S27 | บ่ายสามโมง ฝนยังคงตกต่อเนื่อง ระดับน้ำในซอยตอนนี้ท่วมสูงขึ้นมาถึงหน้าแข้ง หรือราวสามสิบเซนติเมตรแล้ว | `world water_depth_shin / pass hours=3` |
| 71 | 5 | L1-S27 | ข้าวหอมสวมเสื้อกันฝนสีเหลือง เดินออกมาดูสถานการณ์ ก็เห็นคุณป้าข้างบ้านกำลังยืนใช้ไม้กวาดดันน้ำหน้าบ้านอยู่ | `use yellow_raincoat` |
| 72 | 5 | L1-S27 | ข้าวหอมถามข้ามรั้วด้วยความเป็นห่วงว่า ป้าคะ น้ำขึ้นเร็วมาก ป้าเตรียมเก็บของหรือเตรียมตัวอพยพไปศูนย์พักพิงไหมคะ | `mind +2` |
| 73 | 5 | L1-S27 | ป้าโบกมือปฏิเสธทันควันพลางบอกว่า ป้าอยู่บ้านนี้มาสามสิบปีแล้วลูก น้ำไม่เคยท่วมถึงชั้นสอง ยังไงป้าก็ไม่ยอมทิ้งบ้านไปไหน | `world neighbour_aunt_refuse` |
| 74 | 5 | L1-S28 | ข้าวหอมนึกถึงข้อมูลผลสำรวจหลังเฮอริเคนคาทรีนาของสถาบันฟริตซ์ ที่พบว่าคนไม่อพยพสูงถึงร้อยละแปดสิบสอง เพราะไม่อยากทิ้งบ้านตัวเอง | `xp survey_katrina_home Lv1` |
| 75 | 5 | L1-S28 | เดินถัดไป ข้าวหอมเห็นพี่ข้างบ้านกำลังยืนอุ้มสุนัขตัวโปรดไว้แนบอก และมีแมวอีกสามตัวนั่งเบียดกันอยู่บนหลังตู้หน้าบ้าน | `world neighbour_pets` |
| 76 | 5 | L1-S28 | พี่เขาบอกว่า ศูนย์อพยพส่วนใหญ่ไม่อนุญาตให้นำสัตว์เลี้ยงเข้า จะให้ทิ้งหมาแมวไว้ให้อดตายได้ยังไง พี่ยอมติดอยู่ที่นี่ดีกว่า | `mind -3` |
| 77 | 5 | L1-S28 | ซึ่งตรงกับข้อมูลสำรวจของสถาบันฟริตซ์ ที่ระบุว่าร้อยละสี่สิบสี่ของผู้ที่ไม่ยอมอพยพ ตัดสินใจอยู่ต่อเพราะเป็นห่วงสัตว์เลี้ยง | `xp survey_katrina_pets Lv1` |
| 78 | 5 | L1-S29 | ส่วนลุงท้ายซอยถอนหายใจ บอกว่าลุงไม่มีรถยนต์ ไม่มีญาติที่ต่างจังหวัด จะให้อพยพไปไหนก็ไม่รู้ อยู่บ้านยังคุ้นเคยกว่า | `world neighbour_uncle_no_vehicle` |
| 79 | 5 | L1-S29 | และตามข้อมูลสถาบันฟริตซ์ มีถึงร้อยละยี่สิบแปดที่ขาดแคลนทรัพยากร ไม่มีพาหนะเดินทาง และไม่มีที่พักพิงปลายทางที่จะไปได้ | `xp survey_katrina_resources Lv1` |
| 80 | 5 | L1-S30 | ข้าวหอมเข้าใจทุกคนดี การทิ้งบ้านไม่ง่ายเลย จึงเตือนให้ทุกคนเตรียมปลดเบรกเกอร์ชั้นล่างและกักตุนน้ำดื่มสะอาดไว้ให้มากที่สุด | `xp community_advisory Lv1` |
| 81 | 5 | L1-S30 | ฟ้าเริ่มมืดลง ข้าวหอมเดินลุยน้ำกลับเข้าบ้านด้วยใจที่หนักอึ้ง คืนนี้ทุกคนในซอยคงต้องเผชิญหน้ากับวิกฤติน้ำท่วมนี้ไปด้วยกัน | `mind -5 / pass hours=2` |
| 82 | 6 | L1-S31 | เวลาล่วงเลยมาจนถึงเที่ยงคืนตรง ความเงียบปกคลุมไปทั่ว แต่ฝนยังตกกระหน่ำไม่หยุด และลมพัดกระแทกหน้าต่างบ้านดังสนั่น | `pass hours=3 / world midnight_storm` |
| 83 | 6 | L1-S31 | จู่ๆ ข้าวหอมก็ได้ยินเสียงน้ำกระฉอก พอส่องไฟดูก็พบว่าน้ำจากนอกซอยได้ดันทะลักข้ามธรณีประตูเข้ามาในบ้านเรียบร้อยแล้ว | `world water_enters_house` |
| 84 | 6 | L1-S31 | สายน้ำสีขุ่นไหลท่วมพื้นกระเบื้องชั้นล่างอย่างรวดเร็ว ระดับน้ำในบ้านเริ่มแตะตาตุ่มภายในเวลาเพียงไม่กี่นาทีเท่านั้น | `damage hp=-0 / mind -5` |
| 85 | 6 | L1-S32 | ถึงเวลาต้องตัดสินใจ ข้าวหอมไม่ลังเล รีบเดินไปที่ตู้ควบคุมไฟฟ้า แล้วยื่นมือไปปลดเมนเบรกเกอร์ชั้นล่างลงทันที | `use switch_breaker_off` |
| 86 | 6 | L1-S32 | ตามข้อมูลการไฟฟ้านครหลวง การปลดเบรกเกอร์ก่อนน้ำท่วมถึงปลั๊กไฟ เป็นหัวใจสำคัญที่สุดในการป้องกันไฟดูดและรักษาชีวิต | `xp mea_cut_breaker Lv1` |
| 87 | 6 | L1-S33 | เสี้ยววินาทีนั้นเอง เสียงระเบิดดังสนั่น ปัง มาจากหม้อแปลงหน้าปากซอย แสงไฟสีฟ้าสว่างวาบขึ้นสู่ท้องฟ้าแล้วดับมืดลง | `world transformer_blast` |
| 88 | 6 | L1-S33 | ไฟฟ้าทุกบ้านและไฟริมถนนดับพรึบลงพร้อมกัน ซอยทั้งซอยตกอยู่ในความมืดสนิท เหลือเพียงเสียงฝนและเสียงสายน้ำไหลเชี่ยว | `world blackout_entire_soi` |
| 89 | 6 | L1-S34 | ข้าวหอมเปิดไฟฉายในถุงยังชีพ ลำแสงสีขาวส่องฝ่าความมืด ทำให้เห็นผืนน้ำชั้นล่างที่กำลังเพิ่มระดับสูงขึ้นเรื่อยๆ | `use torch / battery_torch -5%` |
| 90 | 6 | L1-S34 | ข้าวหอมสะพายเป้ถุงยังชีพ ก้าวขึ้นบันไดทีละขั้น เพื่อหนีน้ำขึ้นไปปักหลักอยู่บนชั้นสองของบ้านอย่างระมัดระวัง | `pass hours=0.2 / move second_floor` |
| 91 | 6 | L1-S35 | ข้าวหอมหยิบมือถือขึ้นมาดู แสงจอสะท้อนใบหน้า แบตเตอรี่ลดเหลือหกสิบเปอร์เซ็นต์ และแถบสัญญาณเริ่มลดลงเหลือเพียงขีดเดียว | `battery 60% / world signal_dropping` |
| 92 | 6 | L1-S35 | ไฟฟ้าดับ น้ำท่วมชั้นล่าง อาหารในตู้เย็นจะอยู่ได้อีกนานแค่ไหน สัญญาณมือถือจะดับลงเมื่อไหร่ และพรุ่งนี้น้ำจะสูงขึ้นเท่าไหร่ | `mind -5` |
| 93 | 6 | L1-S35 | คืนนี้ข้าวหอมต้องผ่านไปให้ได้ พรุ่งนี้มาร่วมลุ้นและเอาชีวิตรอดในวันที่หนึ่งไปด้วยกันนะคะ อย่าลืมคอมเมนต์ให้กำลังใจกันนะ | `world end_day_0` |

---

## Still list (16:9 wide)
- **L1-S01**: Wide 16:9 shot of a dark bedroom at 3 a.m. with Khao Hom's smartphone screen glowing brightly on the bedside table showing an emergency alert.
- **L1-S02**: Wide 16:9 shot of Khao Hom waking up groggily, sitting up on the bed and reading the urgent notification on her glowing phone.
- **L1-S03**: Wide 16:9 shot of Khao Hom standing by her bedroom window, pulling back the curtain to look out into the heavy stormy rain outside.
- **L1-S04**: Wide 16:9 shot looking down from the window into the dark residential soi, where murky rainwater is rising ankle-deep under a streetlamp.
- **L1-S05**: Wide 16:9 shot of Khao Hom looking determined in her bedroom, checking her fully charged smartphone and wallet on the desk.
- **L1-S06**: Wide 16:9 shot of Khao Hom sitting at her living room desk, checking flood news updates and weather warnings on her phone.
- **L1-S07**: Wide 16:9 shot of Khao Hom opening her front door carefully, holding a long measuring stick to check the water level at the front step.
- **L1-S08**: Wide 16:9 shot looking across the dim, quiet soi where neighbouring houses are completely dark and shuttered while water flows past.
- **L1-S09**: Wide 16:9 shot of Khao Hom counting Thai baht banknotes on her dining table, securing 3,000 baht cash into a clear plastic pouch.
- **L1-S10**: Wide 16:9 shot of Khao Hom wearing her signature bright yellow raincoat, stepping out into the ankle-deep floodwater in front of her gate.
- **L1-S11**: Wide 16:9 shot of a long queue of drenched residents with umbrellas waiting outside a local convenience store in the early morning rain.
- **L1-S12**: Wide 16:9 shot of the convenience store interior with empty shelves where instant noodles and rice have already been completely cleared out.
- **L1-S13**: Wide 16:9 shot of a man greedily piling an entire shelf of bottled water packs into his shopping trolley with a triumphant grin.
- **L1-S14**: Wide 16:9 shot of Khao Hom and waiting shoppers giving deadpan, amusing side-eye glances at the hoarder, keeping her cool.
- **L1-S15**: Wide 16:9 graphic shot of the interactive Choice Card overlaid on screen asking viewers what 3 items they would buy with 3,000 baht.
- **L1-S16**: Wide 16:9 shot of Khao Hom in the store aisle thoughtfully selecting bottled water, canned fish, dry biscuits, and packs of batteries.
- **L1-S17**: Wide 16:9 shot of Khao Hom at the checkout counter paying cash to the cashier, who hands back her receipt and change.
- **L1-S18**: Wide 16:9 shot of Khao Hom trudging back through the rising water carrying heavy bags of supplies as dawn breaks grey and gloomy.
- **L1-S19**: Wide 16:9 shot of Khao Hom inside her ground floor living room, lifting small appliances, microwave, and power strips up onto high furniture.
- **L1-S20**: Wide 16:9 shot of Khao Hom inspecting the main electrical distribution board, applying clear labels to individual circuit breaker switches.
- **L1-S21**: Wide 16:9 educational graphic diagram demonstrating electrical safety, safe separation with dry wood, and calling emergency hotline 1669.
- **L1-S22**: Wide 16:9 shot of Khao Hom in her kitchen thoroughly washing large soup pots, buckets, plastic basins, and clean jugs.
- **L1-S23**: Wide 16:9 shot of Khao Hom filling every clean pot and container to the brim with clean tap water and securing tight lids on them.
- **L1-S24**: Wide 16:9 shot of Khao Hom arranging emergency go-bag supplies on the table: water bottles, canned food, torch, radio, whistle, and first aid kit.
- **L1-S25**: Wide 16:9 shot of Khao Hom sealing her national ID card, household registry, property documents, and remaining cash into double ziplock bags.
- **L1-S26**: Wide 16:9 shot of Khao Hom plugging her smartphone, heavy power banks, and rechargeable flashlight into wall sockets for a 100% full charge.
- **L1-S27**: Wide 16:9 shot of Khao Hom outside in the afternoon wearing her yellow raincoat, talking across the fence to an elderly aunt sweeping floodwater.
- **L1-S28**: Wide 16:9 shot of a female neighbour standing at her front doorway holding her pet dog closely while cats sit perched safely on a high shelf.
- **L1-S29**: Wide 16:9 shot of an elderly uncle leaning against his porch railing, explaining to Khao Hom that he has no car or outside relatives to flee to.
- **L1-S30**: Wide 16:9 shot of Khao Hom walking back to her porch through shin-deep murky water as dusk settles heavily over the quiet flooded neighbourhood.
- **L1-S31**: Wide 16:9 shot at midnight showing murky floodwater breaching the threshold and creeping steadily across the ground floor tiled hallway.
- **L1-S32**: Wide 16:9 shot of Khao Hom with a resolute expression flipping down the main electrical breaker switch for the ground floor circuits.
- **L1-S33**: Wide 16:9 shot of a distant electrical transformer bursting with bright blue sparks in the night rain, followed by instant total blackout across the soi.
- **L1-S34**: Wide 16:9 shot of Khao Hom turning on her emergency LED flashlight, casting a sharp beam across the dark, water-covered living room floor.
- **L1-S35**: Wide 16:9 shot of Khao Hom climbing the stairs carrying her emergency go-bag, looking at her illuminated phone screen showing 60% battery left.

---

## Fact map
- **Row 5, 6**: Fact `T8a` (DDPM Cell Broadcast alert format: agency name, hazard, date/time, hotline 1784; fictional place names per rule).
- **Row 11**: Fact `FACTS §2` (Water rising in soi, ankle depth ~10 cm).
- **Row 13**: `PLAN.md` §4 EP1 (Initial state: 3,000 THB cash budget, 100% battery, inventory in apartment).
- **Row 21**: Fact `FACTS §2` (US NWS: 15 cm / 6 inches of fast-moving floodwater can knock down an adult).
- **Row 22**: Fact `FACTS §2` (กรมอนามัย: 15 cm water causes vehicles to lose control).
- **Row 27**: Fact `T2a` (Hurricane Maria 2017: power outage disables card payments and ATMs; cash demand spikes, cash only).
- **Row 32, 35**: Fact `T3a` (Bangkok 2011: residents hoard dry food/noodles before water arrives; bottled water emptied, egg prices quadrupled).
- **Row 45**: Fact `FACTS §8` / `BIBLE.md` Item Rule 5 / `FACTS-items.md` I1 (US CDC: use flashlights instead of candles during power outages).
- **Row 46**: Fact `FACTS §8` (Ready.gov / กรมอนามัย: non-perishable ready-to-eat dry food supply).
- **Row 51**: Fact `FACTS §1` (กรมอนามัย: switch off electrical appliances, gas stove, lift/trip breaker before disaster).
- **Row 52, 53**: Fact `FACTS §1` (MEA / กฟน.: prepare to switch off main breaker when water approaches house; never touch switches or appliances while wet or in water).
- **Row 54**: Fact `FACTS §1` (กรมอนามัย: label fuse and breaker switches to indicate which areas of house they control).
- **Row 55, 56, 57**: Fact `FACTS §10` (กรมอนามัย & PEA: electric shock rescue in flood — never enter with bare hands or wade in; cut breaker first; isolate with dry non-conductive wood/plastic/cloth; call 1669; CPR chest compression depth 5-6 cm at 100-120/min; send to hospital every case).
- **Row 58, 60**: Fact `FACTS §3` (Ready.gov FEMA: store at least 1 gallon / 3.8 L per person per day for several days; กรมอนามัย: 4 storage steps, clean sealed containers).
- **Row 62, 63, 64**: Fact `FACTS §8` (Ready.gov FEMA & กรมอนามัย: grab bag / emergency kit — water, food, torch + extra batteries, battery radio, first aid kit + personal meds, whistle).
- **Row 65, 66**: Fact `FACTS §8` (Ready.gov FEMA: family important documents saved in portable waterproof container).
- **Row 73, 74**: Fact `T5b` (Katrina Fritz Institute/Harris survey: 82% of those who chose to stay cited not wanting to leave home / living there 30 years).
- **Row 76, 77**: Fact `T5b` (Katrina Fritz Institute/Harris survey: 44% cited pets as reason for not evacuating).
- **Row 78, 79**: Fact `T5b` (Katrina Fritz Institute/Harris survey: 28% lacked resources, vehicle, or place to go).
- **Row 85, 86**: Fact `FACTS §1` (MEA / กฟน.: cut main breaker before water reaches sockets).
- **Row 87, 88**: Fact `T9` / `PLAN.md` (Local power cut in flooded soi; transformer failure).
- **Row 91, 92**: `PLAN.md` §4 EP1 / Fact `T1b` (Phone battery down to 60% at midnight, mobile towers begin losing backup power).

---

## Not checked / risk
- Thai official litres-per-person flood storage figure is NOT FOUND in opened pages (US Ready.gov 1 gallon ≈ 3.8 L figure used with explicit attribution).
- Thai official day-count for storing water is NOT FOUND in opened pages (Ready.gov "several days" used).
- Thai ปภ. official grab-bag checklist page was NOT FOUND in opened pages; the Ready.gov emergency kit checklist cross-referenced with กรมอนามัย summary list was used.
- MEA official power-cut water height rule was NOT FOUND (T9); the script strictly avoids claiming a specific water depth for grid cutoff and attributes the blackout to a local transformer failure.
- Cell Broadcast alert text uses fictional subdistrict and canal names (`ตำบลริมคลอง`) per the brief's explicit instruction to use no real place names.
- All store prices are round estimates explicitly marked as fictional `(ราคาสมมติ)` per brief instruction.
